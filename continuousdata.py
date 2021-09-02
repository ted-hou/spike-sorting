import os
import warnings
from datetime import datetime
from dataclasses import dataclass
from typing import Sequence
import numpy as np


class ContinuousData:
    @dataclass
    class ChannelInfo:
        electrode_id: int  # Electrode number.
        label: str  # Label or name of the electrode (e.g. “chan1”).
        analog_units: str  # Units of the analog range values (“mV”, “μV”).
        high_freq_cutoff: float  # High frequency cutoff (Hz) used in bandpass filter: Inf = None
        low_freq_cutoff: float  # Low frequency cutoff (Hz) used in bandpass filter: 0 = None

    file: str  # path to continuous data file
    data: np.ndarray  # continuous data with shape (num_samples, num_channels)
    time_origin: datetime  # UTC time at first sample in file
    channels: [int]  # zero-based indices indicating which channels were read from file
    electrodes: [int]  # electrode ids read from file (this is usually a 1-based index)
    sample_rate: float  # sampling rate in Hz
    channels_info: [ChannelInfo]
    n_samples: int
    n_channels: int

    def filter(self, low_freq=250.0, high_freq=5000.0) -> np.ndarray:
        pass


class BlackrockContinuousData(ContinuousData):
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
            self.analog_units = data[30:46].rstrip(b'\x00').decode()
            self.high_freq_cutoff = int.from_bytes(data[46:50], byteorder='little', signed=False) / 1000
            self.high_freq_order = int.from_bytes(data[50:54], byteorder='little', signed=False)
            self.high_filter_type = 'Butterworth' if int.from_bytes(data[54:56], byteorder='little',
                                                                    signed=False) > 0 else 'None'
            self.low_freq_cutoff = int.from_bytes(data[56:60], byteorder='little', signed=False) / 1000
            self.low_freq_order = int.from_bytes(data[60:64], byteorder='little', signed=False)
            self.low_filter_type = 'Butterworth' if int.from_bytes(data[64:66], byteorder='little',
                                                                   signed=False) > 0 else 'None'

    @dataclass
    class __NSxHeader:
        file_type_id: str  # Always set to “BRSMPGRP” for “Neural Continuous Data”. Note: In prior versions of the
        # file, this field was set to “NEURALSG” or “NEURALCD”.
        file_spec: float  # The major and minor revision numbers of the file specification used to create the file
        # e.g. use 0x0202 for Spec. 2.2.
        bytes_in_headers: int  # The total number of bytes in both headers (Standard and Extended). This value can
        # also be considered to be a zeroindexed pointer to the first data packet.
        label: str  # Label of the sampling group e.g. “1 kS/s” or “LFP Low”. Must be ’0’ terminated.
        sample_rate: float  # Sampling rate in Hz
        time_origin: datetime  # Windows UTC time at start of acquisition, corresponds to timestamp = 0.
        n_channels: int  # Number of channels per data point.
        channels_info = []

        def __init__(self, file):
            with open(file, mode='rb') as file:
                self.file_type_id = file.read(8).decode()
                self.file_spec = ord(file.read(1)) + 0.1 * ord(file.read(1))
                self.bytes_in_headers = int.from_bytes(file.read(4), byteorder='little', signed=False)
                self.label = file.read(16).rstrip(b'\x00').decode()
                file.seek(256, 1)  # Skip the comments
                period = int.from_bytes(file.read(4), byteorder='little', signed=False)
                self.sample_rate = int.from_bytes(file.read(4), byteorder='little', signed=False) / period
                self.time_origin = self.bytes_to_datetime(file.read(16))
                self.n_channels = int.from_bytes(file.read(4), byteorder='little', signed=False)
                self.channels_info = [BlackrockContinuousData.ChannelInfo(file.read(66)) for _ in
                                      range(0, self.n_channels)]
            if self.file_type_id == 'NEURALSG':
                raise ValueError(
                    f"Blackrock NSx file type '{self.file_type_id}' (2.1) is not supported. Must be 'NEURALCD' or 'BRSMPGRP'")

        @staticmethod
        def bytes_to_datetime(data: bytes):
            yy = int.from_bytes(data[0:2], byteorder='little', signed=False)
            mo = int.from_bytes(data[2:4], byteorder='little', signed=False)
            dd = int.from_bytes(data[6:8], byteorder='little', signed=False)
            hh = int.from_bytes(data[8:10], byteorder='little', signed=False)
            mm = int.from_bytes(data[10:12], byteorder='little', signed=False)
            ss = int.from_bytes(data[12:14], byteorder='little', signed=False)
            us = int.from_bytes(data[14:16], byteorder='little', signed=False) * 1000

            return datetime(yy, mo, dd, hh, mm, ss, us)

    __header: __NSxHeader

    def read(self, file: str, electrodes: Sequence[int] = None, channels: Sequence[int] = None,
             n_samples: int = 0xFFFFFFFF):
        """Read header + continuous data from NSx file.

        :param file: path to .NSx file
        :param electrodes: list of electrode IDs to read frsom. Used to search in __NSxHeader.channels_info.id (default None reads all electrodes). This takes priority over 'channels'
        :param channels: list of (0-based) channel indices to read from. Range from 0 to N-1, where N is number of recorded channels in file. (default None reads all channels)
        :param n_samples: number of samples to read. (default/max value: 0xFFFFFFFF)
        :return: None
        """
        if n_samples > 0xFFFFFFFF:
            warnings.warn(f"Parameter n_samples ({n_samples:x}) is capped at {0xFFFFFFFF:x}")
            n_samples = 0xFFFFFFFF

        self.file = file
        self.__header, self.time_origin, self.sample_rate = self.__read_header(file)
        self.data, self.channels, self.electrodes, self.channels_info = self.__read_data(file, electrodes, channels, n_samples)
        self.n_samples = self.data.shape[0]
        self.n_channels = self.data.shape[1]

    def __read_header(self, file):
        header = self.__NSxHeader(file)
        return header, header.time_origin, header.sample_rate

    def __read_data(self, file, electrodes: Sequence[int] = None, channels: Sequence[int] = None,
                    n_samples: int = 0xFFFFFFFF) -> (np.ndarray, [int], [int]):
        packet_start = self.__header.bytes_in_headers
        with open(file, mode='rb') as file:
            # Read data packet __header
            file.seek(packet_start, os.SEEK_SET)
            packet_header = file.read(1)
            assert packet_header == b'\x01'  # Blackrock data packets always start with 0x01
            if self.__header.file_type_id == 'NEURALCD':
                packet_start_timestamp = int.from_bytes(file.read(4), byteorder='little', signed=False)
            elif self.__header.file_type_id == 'BRSMPGRP':
                packet_start_timestamp = int.from_bytes(file.read(8), byteorder='little', signed=False)
            assert packet_start_timestamp == 0

            # Determine number of samples to read
            packet_n_samples = int.from_bytes(file.read(4), byteorder='little', signed=False)
            n_samples = min(n_samples, packet_n_samples)

            channels, electrodes = self.__validate_sel_channels(channels, electrodes)

            n_channels = len(channels)
            trimmed_electrodes_info = [self.__header.channels_info[c] for c in channels]

            # Simple case, read all channels
            if n_channels == self.__header.n_channels:
                data = np.fromfile(file, dtype=np.int16, count=n_channels * n_samples)
                data = np.reshape(data, (n_samples, n_channels), order='C')
            else:
                range_samples = range(n_samples)
                data = np.ndarray((n_samples, n_channels), dtype=np.int16)

                cur_chn = 0  # Absolute channel index from file
                for i_sample in range_samples:
                    i = 0  # Consolidated channel index
                    while i < len(channels):
                        file.seek(2*(channels[i] - cur_chn), os.SEEK_CUR)
                        # cur_chn = channels[i]
                        data[i_sample, i] = np.frombuffer(file.read(2),
                                                          dtype=np.int16)  # Should default to little-endian order
                        cur_chn = channels[i] + 1
                        i += 1
                    file.seek(2*(self.__header.n_channels - cur_chn), os.SEEK_CUR)
                    cur_chn = 0

        return data, channels, electrodes, trimmed_electrodes_info

    def __validate_sel_channels(self, channels, electrodes):
        # Determine which channels to read
        # Select via electrode ID
        if electrodes is not None and electrodes:
            sel_electrodes = [*electrodes].copy()
            electrodes_in_file = [e.electrode_id for e in self.__header.channels_info]
            electrodes = [e for e in electrodes if e in electrodes_in_file]
            channels = [electrodes_in_file.index(e) for e in electrodes]
            if not channels:
                raise ValueError(f'None of the specified electrodes are in file {[*sel_electrodes]}.')
        # Select via channel index (0-based)
        elif channels is not None and channels:
            sel_channels = [*channels].copy()
            channels = [c for c in channels if c < self.__header.n_channels]
            electrodes = [self.__header.channels_info[c].electrode_id for c in channels]
            if not channels:
                raise ValueError(f'None of the specified channels are in file {[*sel_channels]}.')
        # Read all channels (no selection criteria provided)
        else:
            channels = [*range(self.__header.n_channels)]
            electrodes = [self.__header.channels_info[c].electrode_id for c in channels]

        return channels, electrodes
