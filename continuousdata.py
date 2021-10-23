from __future__ import annotations  # allows TreeItem type hint in its own constructor
import os
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Sequence
import numpy as np
import numpy.random


class ContinuousData:
    @dataclass
    class ChannelInfo:
        electrode_id: int  # Electrode number.
        label: str  # Label or name of the electrode (e.g. “chan1”).
        analog_units: str  # Units of the analog range values (“mV”, “μV”).
        high_freq_cutoff: float  # High frequency cutoff (Hz) used in bandpass filter: Inf = None
        low_freq_cutoff: float  # Low frequency cutoff (Hz) used in bandpass filter: 0 = None
        conversion_factor: float  # Multiply by this value to convert data from int16 to float64

        def __init__(self, electrode_id: int, label: str = '', analog_units: str = 'μV', high_freq_cutoff: float = None, low_freq_cutoff: float = None, conversion_factor: float = 1.0):
            self.electrode_id = electrode_id
            self.label = label
            self.analog_units = analog_units
            self.high_freq_cutoff = high_freq_cutoff
            self.low_freq_cutoff = low_freq_cutoff
            self.conversion_factor = conversion_factor

    file: str  # path to continuous data file
    data: np.ndarray  # int16 representation of continuous data with shape (num_samples, num_channels). Needs to be multiplied with conversion_factor for actual voltage
    time_origin: datetime  # UTC time at first sample in file
    channels: [int]  # zero-based indices indicating which channels were read from file
    electrodes: [int]  # electrode ids read from file (this is usually a 1-based index)
    sample_rate: float  # sampling rate in Hz
    channels_info: [ChannelInfo]
    n_samples: int
    n_channels: int

    def filter(self, low_freq=250.0, high_freq=5000.0) -> np.ndarray:
        pass

    @staticmethod
    def generate(n_channels=32, min_spike_rate=10.0, max_spike_rate=60.0, sample_rate=30000, n_samples=300000, seed: int = None):
        """Generate simulated data."""
        cd = ContinuousData()
        cd.file = None
        cd.time_origin = datetime.now(timezone.utc)
        cd.channels = list(range(n_channels))
        cd.electrodes = list(range(1, n_channels + 1))
        cd.sample_rate = sample_rate
        cd.n_samples = n_samples
        cd.n_channels = n_channels
        cd.channels_info = [ContinuousData.ChannelInfo(i + 1, label=f"chan{i + 1}", conversion_factor=0.25) for i in range(n_channels)]

        # Generate spike train
        # Random firing rates for each channel
        rng = numpy.random.default_rng(seed)
        fr = (max_spike_rate - min_spike_rate) * rng.random(size=n_channels) + min_spike_rate

        # Firing probability for each discrete time point is (fr * dt), equivalent to (ft / sample_rate)
        spike_train = rng.random(size=(n_samples, n_channels)) * sample_rate < fr

        # Generate a standard waveform for each channel
        def generate_waveform(phase_durations=(.0002, .0003, .0005), depolarization_voltage=-200.0, hyperpolarization_voltage=50.0):
            # Generate discrete times and corresponding voltages (td, vd)
            dur = list(phase_durations)
            dur.insert(0, 0)
            dur.insert(1, dur[1] * 0.05)
            dur[2] *= 0.95
            dur.insert(4, dur[4] * 0.5)
            dur[5] *= 0.5
            td = np.asarray(dur).cumsum()
            vd = np.asarray([0, 0, depolarization_voltage, hyperpolarization_voltage, hyperpolarization_voltage*0.367879, 0])
            # Spline interpolation of td, vd -> ts, vs
            from scipy.interpolate import splrep, splev
            spl = splrep(td, vd, per=True)
            ts = np.arange(0, td[-1], 1/sample_rate)
            vs = splev(ts, spl)
            return vs

        phase_durations_mean = np.asarray((.0001, .00015, .00025))
        phase_durations_sd_scale = np.asarray(0.1)
        phase_durations = rng.normal(
            loc=phase_durations_mean,
            scale=phase_durations_sd_scale * phase_durations_mean,
            size=(n_channels, 3)
        )

        # Convolve spike-train with waveform shape
        data_f = np.empty((n_samples, n_channels), dtype=np.float64)
        for i_channel in range(n_channels):
            waveform = generate_waveform(phase_durations=phase_durations[i_channel, :],
                                         depolarization_voltage=rng.normal(loc=-300, scale=50),
                                         hyperpolarization_voltage=rng.normal(loc=100, scale=50))
            data_f[:, i_channel] = np.convolve(spike_train[:, i_channel], waveform, 'same')

        # Add noise and convert to int
        white_noise = 100.0 * rng.standard_normal(size=data_f.shape, dtype=np.float64)
        from scipy import signal
        sos = signal.butter(2, 7500, btype='lowpass', output='sos', fs=sample_rate)
        data_f += signal.sosfilt(sos, white_noise)
        cd.data = np.rint(data_f * 4).astype(np.int16)

        return cd


class BlackrockContinuousData(ContinuousData):
    packet_index: int
    packet_sample_offset: int

    @dataclass
    class ChannelInfo(ContinuousData.ChannelInfo):
        type: str  # Always set to “CC” for “Continuous Channels”
        bank: int  # Physical system connector or module connected to the electrode (e.g. Front-End Bank A, B, C,
        # D are 1, 2, 3, 4).
        pin: int  # Physical system connector pin or channel connected to the electrode (e.g. 1-37 on bank A, B, C, D).
        min_digital_value: int  # Minimum digital value of the signal (e.g. -8192).
        max_digital_value: int  # Maximum digital value of the signal (e.g. 8192).
        min_analog_value: int  # Minimum analog value of the signal (e.g. -5000 mV).
        max_analog_value: int  # Maximum analog value of the signal (e.g. 5000 mV).
        high_freq_order: int  # Order of the filter used for high frequency cutoff: 0 = NONE
        high_filter_type: str  # Type of filter used for high frequency cutoff: 0 = NONE, 1 = Butterworth
        low_freq_order: int  # Order of the filter used for high frequency cutoff: 0 = NONE
        low_filter_type: str  # Type of filter used for high frequency cutoff: 0 = NONE, 1 = Butterworth

        def __init__(self, data: bytes):
            self.type = data[0:2].decode()
            self.electrode_id = int.from_bytes(data[2:4], byteorder='little', signed=False)
            self.label = data[4:20].rstrip(b'\x00').decode()
            self.bank = int(data[20])
            self.pin = int(data[21])
            self.min_digital_value = int.from_bytes(data[22:24], byteorder='little', signed=True)
            self.max_digital_value = int.from_bytes(data[24:26], byteorder='little', signed=True)
            self.min_analog_value = int.from_bytes(data[26:28], byteorder='little', signed=True)
            self.max_analog_value = int.from_bytes(data[28:30], byteorder='little', signed=True)
            self.conversion_factor = self.max_analog_value / self.max_digital_value
            self.analog_units = data[30:46].rstrip(b'\x00').decode()
            self.high_freq_cutoff = int.from_bytes(data[46:50], byteorder='little', signed=False) / 1000
            self.high_freq_order = int.from_bytes(data[50:54], byteorder='little', signed=False)
            self.high_filter_type = 'Butterworth' if int.from_bytes(data[54:56], byteorder='little',
                                                                    signed=False) > 0 else 'None'
            self.low_freq_cutoff = int.from_bytes(data[56:60], byteorder='little', signed=False) / 1000
            self.low_freq_order = int.from_bytes(data[60:64], byteorder='little', signed=False)
            self.low_filter_type = 'Butterworth' if int.from_bytes(data[64:66], byteorder='little',
                                                                   signed=False) > 0 else 'None'

    def __init__(self, file: str, data: np.ndarray, sample_rate: float, channels: Sequence[int], electrodes: Sequence[int], channels_info: Sequence[ChannelInfo], time_origin: datetime, packet_index: int = 0, packet_sample_offset: int = 0):
        self.file = file
        self.data = data
        self.sample_rate = sample_rate
        self.channels = channels
        self.electrodes = electrodes
        self.channels_info = channels_info
        self.packet_index = packet_index
        self.packet_sample_offset = packet_sample_offset
        if packet_sample_offset > 0:
            self.time_origin = time_origin + timedelta(seconds=packet_sample_offset/sample_rate)
        else:
            self.time_origin = time_origin
        self.n_samples = data.shape[0]
        self.n_channels = data.shape[1]

    @staticmethod
    def fromfile(file: str, electrodes: Sequence[int] = None, channels: Sequence[int] = None, n_samples: int = 0xFFFFFFFF, packet_mode='last'):
        """Read header + continuous data from NSx file.

        :param file: path to .NSx file
        :param electrodes: list of electrode IDs to read frsom. Used to search in __NSxHeader.channels_info.id (default None reads all electrodes). This takes priority over 'channels'
        :param channels: list of (0-based) channel indices to read from. Range from 0 to N-1, where N is number of recorded channels in file. (default None reads all channels)
        :param n_samples: number of samples to read. (default/max value: 0xFFFFFFFF)
        :param packet_mode: read 'first', 'last', or 'all', only used in case multiple data packets are in one NSx file
        :return: BlackrockContinuousData object, or list[BlackrockContinuousData] if packet_mode is 'all'
        """
        if n_samples > 0xFFFFFFFF:
            warnings.warn(f"Parameter n_samples ({n_samples:x}) is capped at {0xFFFFFFFF:x}")
            n_samples = 0xFFFFFFFF

        file_type_id, bytes_in_header, sample_rate, time_origin, n_channels_in_file, channels_info = BlackrockContinuousData._read_header(file)

        channels, electrodes, channels_info = BlackrockContinuousData._validate_sel_channels(channels, electrodes, n_channels_in_file, channels_info)

        packet_index = -1
        packet_sample_offset = 0
        packet_n_samples = 0
        prev_packet_n_samples = 0
        packet_start_pos = 0

        # Read all packets
        if packet_mode == 'all':
            n_samples_read = 0
            is_eof = False
            packet_end_pos = bytes_in_header
            cd_list = []
            while not is_eof and n_samples_read < n_samples:
                # Scan size of next data packet
                packet_index += 1
                is_eof, packet_start_pos, packet_n_samples, packet_end_pos, packet_sample_offset = \
                    BlackrockContinuousData._scan_next_packet(file, file_type_id, n_channels_in_file, packet_end_pos)

                # Timing correction required
                if packet_index > 0 and packet_sample_offset == 0:
                    time_origin += timedelta(seconds=prev_packet_n_samples/sample_rate)
                prev_packet_n_samples = packet_n_samples

                # Read next data packet
                n_samples_to_read_from_packet = min(n_samples - n_samples_read, packet_n_samples)
                data = BlackrockContinuousData._read_next_packet(file, packet_start_pos, channels,
                                                                 n_samples_to_read_from_packet, n_channels_in_file)
                n_samples_read -= n_samples_to_read_from_packet
                cd_list.append(BlackrockContinuousData(file, data, sample_rate, channels, electrodes, channels_info,
                                                  time_origin, packet_index, packet_sample_offset))
            return cd_list
        # Only read first packet
        elif packet_mode == 'first':
            packet_index += 1
            _, packet_start_pos, packet_n_samples, _, packet_sample_offset = \
                BlackrockContinuousData._scan_next_packet(file, file_type_id, n_channels_in_file, bytes_in_header)
        # Only read last packet (this is what makes sense for my 2-rig recording setup)
        elif packet_mode == 'last':
            is_eof = False
            packet_end_pos = bytes_in_header
            while not is_eof:
                packet_index += 1
                is_eof, packet_start_pos, packet_n_samples, packet_end_pos, packet_sample_offset = \
                    BlackrockContinuousData._scan_next_packet(file, file_type_id, n_channels_in_file, packet_end_pos)

                # Timing correction required
                if packet_index > 0 and packet_sample_offset == 0:
                    time_origin += timedelta(seconds=prev_packet_n_samples/sample_rate)
                prev_packet_n_samples = packet_n_samples

        else:
            raise ValueError(f"Unknown packet_mode '{packet_mode}', only 'first', 'last', and 'all' are supported.")

        # Below: only executed when packet_mode is 'first' or 'last'
        if n_samples > packet_n_samples:
            warnings.warn(f"Requested {n_samples} samples but the {packet_mode} data packet only contains {packet_n_samples}.")
        n_samples = min(n_samples, packet_n_samples)
        data = BlackrockContinuousData._read_next_packet(file, packet_start_pos, channels, n_samples, n_channels_in_file)

        cd = BlackrockContinuousData(file, data, sample_rate, channels, electrodes, channels_info, time_origin, packet_index, packet_sample_offset)
        return cd

    @staticmethod
    def _read_header(file):
        """
        :return:
        file_type_id: str, Always set to “BRSMPGRP” for “Neural Continuous Data”. Note: In prior versions of the file, this field was set to “NEURALSG” or “NEURALCD”.
        bytes_in_headers: int, The total number of bytes in both headers (Standard and Extended). This value can also be considered to be a zeroindexed pointer to the first data packet.
        label: str, Label of the sampling group e.g. “1 kS/s” or “LFP Low”. Must be ’0’ terminated.
        sample_rate: float, Sampling rate in Hz
        time_origin: datetime, Windows UTC time at start of acquisition, corresponds to timestamp = 0.
        n_channels: int, Number of channels per data point.
        channels_info = []
        """
        with open(file, mode='rb') as file:
            file_type_id = file.read(8).decode()
            file.seek(2, os.SEEK_CUR)  # file_spec = ord(file.read(1)) + 0.1 * ord(file.read(1))
            bytes_in_header = int.from_bytes(file.read(4), byteorder='little', signed=False)
            file.seek(16, os.SEEK_CUR)  # label = file.read(16).rstrip(b'\x00').decode()
            file.seek(256, os.SEEK_CUR)  # Comments
            period = int.from_bytes(file.read(4), byteorder='little', signed=False)
            assert period == 1
            sample_rate = int.from_bytes(file.read(4), byteorder='little', signed=False) / period

            # Convert file-start windows-time (UTC) to datetime object (UTC)
            time_origin = file.read(16)
            yy = int.from_bytes(time_origin[0:2], byteorder='little', signed=False)
            mo = int.from_bytes(time_origin[2:4], byteorder='little', signed=False)
            dd = int.from_bytes(time_origin[6:8], byteorder='little', signed=False)
            hh = int.from_bytes(time_origin[8:10], byteorder='little', signed=False)
            mm = int.from_bytes(time_origin[10:12], byteorder='little', signed=False)
            ss = int.from_bytes(time_origin[12:14], byteorder='little', signed=False)
            us = int.from_bytes(time_origin[14:16], byteorder='little', signed=False) * 1000
            time_origin = datetime(yy, mo, dd, hh, mm, ss, us, tzinfo=timezone.utc)

            n_channels = int.from_bytes(file.read(4), byteorder='little', signed=False)
            channels_info = [BlackrockContinuousData.ChannelInfo(file.read(66)) for _ in range(0, n_channels)]
            if file_type_id == 'NEURALSG':
                raise ValueError(f"Blackrock NSx file type '{file_type_id}' (2.1) is not supported. Must be 'NEURALCD' or 'BRSMPGRP'")

            return file_type_id, bytes_in_header, sample_rate, time_origin, n_channels, channels_info

    @staticmethod
    def _scan_next_packet(file, file_type_id: str, n_channels: int, offset: int) -> (bool, int):
        """
        :return:
        packet_end_is_eof: True if this packet ends at the end of file
        packet_end_pos: use this as base for scanning next packet
        packet_sample_offset: this / sample_rate + header.time_origin is packet start time
        """
        with open(file, mode='rb') as file:
            file.seek(offset, os.SEEK_SET)

            # Each packet starts with a 0x01
            packet_header = file.read(1)
            if packet_header != b'\x01':
                raise ValueError(f"Blackrock data packets should always start with 0x01, got {packet_header.hex()} instead")

            if file_type_id == 'NEURALCD':
                packet_sample_offset = int.from_bytes(file.read(4), byteorder='little', signed=False)
            elif file_type_id == 'BRSMPGRP':
                packet_sample_offset = int.from_bytes(file.read(8), byteorder='little', signed=False)
            else:
                raise ValueError(f"Blackrock NSx file type '{file_type_id}' is not supported. Must be 'NEURALCD' or 'BRSMPGRP'")

            packet_n_samples = int.from_bytes(file.read(4), byteorder='little', signed=False)
            packet_start_pos = file.tell()
            packet_end_pos = file.seek(2 * packet_n_samples * n_channels, os.SEEK_CUR)
            file_end_pos = file.seek(0, os.SEEK_END)
            packet_end_is_eof = packet_end_pos == file_end_pos

        return packet_end_is_eof, packet_start_pos, packet_n_samples, packet_end_pos, packet_sample_offset

    @staticmethod
    def _read_next_packet(file, packet_start, channels: Sequence[int], n_samples: int, n_channels_in_file: int):
        with open(file, mode='rb') as file:
            file.seek(packet_start, os.SEEK_SET)

            # Simple case, read all channels
            n_channels = len(channels)
            if n_channels == n_channels_in_file:
                data = np.fromfile(file, dtype=np.int16, count=n_channels * n_samples)
                data = np.reshape(data, (n_samples, n_channels), order='C')
            # Read subset of channels
            else:
                range_samples = range(n_samples)
                data = np.ndarray((n_samples, n_channels), dtype=np.int16)

                cur_chn = 0  # Absolute channel index from file
                for i_sample in range_samples:
                    i = 0  # Consolidated channel index
                    while i < len(channels):
                        file.seek(2*(channels[i] - cur_chn), os.SEEK_CUR)
                        data[i_sample, i] = np.frombuffer(file.read(2), dtype=np.int16)  # Should default to little-endian order
                        cur_chn = channels[i] + 1
                        i += 1
                    file.seek(2 * (n_channels_in_file - cur_chn), os.SEEK_CUR)
                    cur_chn = 0
        return data

    @staticmethod
    def _validate_sel_channels(channels, electrodes, n_channels_in_file: int, channels_info: list[ChannelInfo]):
        # Determine which channels to read
        # Select via electrode ID
        if electrodes is not None and electrodes:
            sel_electrodes = [*electrodes].copy()
            electrodes_in_file = [ci.electrode_id for ci in channels_info]
            electrodes = [e for e in electrodes if e in electrodes_in_file]
            channels = [electrodes_in_file.index(e) for e in electrodes]
            if not channels:
                raise ValueError(f'None of the specified electrodes are in file {[*sel_electrodes]}.')
        # Select via channel index (0-based)
        elif channels is not None and channels:
            sel_channels = [*channels].copy()
            channels = [c for c in channels if c < n_channels_in_file]
            electrodes = [channels_info[c].electrode_id for c in channels]
            if not channels:
                raise ValueError(f'None of the specified channels are in file {[*sel_channels]}.')
        # Read all channels (no selection criteria provided)
        else:
            channels = [*range(n_channels_in_file)]
            electrodes = [channels_info[c].electrode_id for c in channels]

        trimmed_channels_info = [channels_info[c] for c in channels]

        return channels, electrodes, trimmed_channels_info
