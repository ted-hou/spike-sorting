import copy
import time
from continuousdata import ContinuousData
import numpy as np
from scipy.signal import find_peaks


class SpikeDetectConfig:
    direction: int
    n_sigmas = 0.0
    n_sigmas_return = None
    n_sigmas_reject = None
    waveform_window: tuple[float, float]
    sd = None
    threshold = 0.0
    threshold_return = None
    threshold_reject = None

    def __init__(self, direction=-1, n_sigmas=3.0, n_sigmas_return=1.5, n_sigmas_reject=40.0,
                 waveform_window=(-.5, .5), sd=None):
        direction = 1 if direction > 0 else -1
        self.direction = direction
        self.n_sigmas = n_sigmas
        self.n_sigmas_return = n_sigmas_return
        self.n_sigmas_reject = n_sigmas_reject
        self.waveform_window = waveform_window
        self.set_sd(sd)

    def set_sd(self, value):
        self.sd = value

        if value is None:
            self.threshold = 0.0
            self.threshold_return = None
            self.threshold_reject = None
        else:
            self.threshold = value * self.n_sigmas * self.direction
            self.threshold_return = None if self.n_sigmas_return is None else value * self.n_sigmas_return * self.direction
            self.threshold_reject = None if self.n_sigmas_reject is None else value * self.n_sigmas_reject * self.direction

        return self


def estimate_sd(data):
    """
    Use (median absolute deviation / 0.6745) as an estimate of standard deviation

    :param data: continuous data, either ContinuousData or NumPy array with shape (n_samples, n_channels)
    :return: 1-d numpy array containing standard deviation estimates for each channel
    """
    if isinstance(data, ContinuousData):
        data = data.data

    if isinstance(data, np.ndarray):
        return np.median(np.abs(data - np.median(data, axis=0)), axis=0) / 0.6745
    else:
        raise TypeError(f"param 'data' is type {type(data)}, expected numpy.ndarray or ContinuousData.")


def find_waveforms(data, sample_rate=None, electrode_map=None, direction=-1, n_sigmas=3.0, n_sigmas_return=1.5,
                   n_sigmas_reject=40.0,
                   waveform_window=(-.5, .5), config: SpikeDetectConfig = None):
    """
    Find waveforms. Uses scipy.signal.find_peaks for spike detection. This is 20x faster than custom python code.

    :param data: continuous data, either ContinuousData or numpy.ndarray with shape (n_samples, n_channels)
    :param sample_rate: sampling rate (Hz). Auto-extracted if data is ContinuousData type
    :param electrode_map: (optional) electrode IDs for each channel. Auto-extracted if data is ContinuousData type
    :param direction: negative number finds negative peaks, positive number finds positive peaks (default -1)
    :param n_sigmas: spike detection threshold, specified as number of standard deviations (default 3.0)
    :param n_sigmas_return: spike rejection threshold, to exclude large artefact (default 40.0, use None to ignore)
    :param n_sigmas_reject: spike must return to this threshold within waveform_window (default 1.5, use None to ignore)
    :param waveform_window: window in milliseconds extracted around peak of waveform (default (-1.0, 1.0))
    :param config: spikedetect.SpikeDetectConfig object, overrides all other params if provided (default None)
    :return:
    """
    if isinstance(data, ContinuousData):
        sample_rate = data.sample_rate
        electrode_map = data.electrodes
        data = data.data

    sd = estimate_sd(data)
    if config is None:
        configs = [SpikeDetectConfig(direction, n_sigmas, n_sigmas_return, n_sigmas_reject, waveform_window, this_sd)
                   for this_sd in sd]
    else:
        configs = [copy.copy(config).set_sd(this_sd) for this_sd in sd]

    (n_samples, n_channels) = data.shape
    waveform_window_samples = np.rint(np.array(waveform_window) * sample_rate / 1000.0).astype(int)

    n_samples_per_waveform = -waveform_window_samples[0] + waveform_window_samples[1] + 1

    from spikedata import SpikeData
    spike_data = [SpikeData(channel=i, sample_rate=sample_rate, electrode=None if electrode_map is None else electrode_map[i], detect_config=configs[i]) for i in
                  range(n_channels)]

    for chn in range(n_channels):
        direction = configs[chn].direction
        threshold = configs[chn].threshold
        threshold_return = None if configs[chn].threshold_return is None else configs[chn].threshold_return
        threshold_reject = None if configs[chn].threshold_reject is None else configs[chn].threshold_reject

        if threshold_reject is not None:
            i_peaks, _ = find_peaks(data[:, chn] * direction, height=(threshold*direction, threshold_reject*direction))
        else:
            i_peaks, _ = find_peaks(data[:, chn] * direction, height=threshold*direction)

        n_waveforms = len(i_peaks)
        spike_data[chn].waveforms = np.empty((n_waveforms, n_samples_per_waveform), dtype=np.int16, order='C')
        spike_data[chn].sample_indices = np.empty((n_waveforms,), dtype=np.int32)
        spike_data[chn].waveform_timestamps = np.array(
            [t / sample_rate for t in range(waveform_window_samples[0], waveform_window_samples[1] + 1)])
        assert spike_data[chn].waveform_timestamps.size == n_samples_per_waveform

        i_waveform = 0
        for i_sample in i_peaks:
            waveform = data[i_sample + waveform_window_samples[0]:i_sample + waveform_window_samples[1] + 1, chn]
            if __validate_waveform(waveform, -waveform_window_samples[0], threshold_return, direction, n_samples_per_waveform):
                spike_data[chn].waveforms[i_waveform, :] = waveform
                spike_data[chn].sample_indices[i_waveform] = i_sample
                i_waveform += 1

        # Cull invalid waveforms and indices from the over-allocated arrays
        if i_waveform < n_waveforms:
            # NOTE: np.ndarray.resize() flattens in memory order, reallocates and then reshapes.
            # This means a C-contiguous array is correctly resized when trimmed ONLY along axis=0
            assert spike_data[chn].waveforms.flags.c_contiguous
            spike_data[chn].waveforms.resize((i_waveform, n_samples_per_waveform))
            spike_data[chn].sample_indices.resize((i_waveform,))

        spike_data[chn].timestamps = spike_data[chn].sample_indices / sample_rate

    return spike_data


def __validate_waveform(waveform, center_index, threshold_return, direction, n_samples_per_waveform) -> bool:
    """Returns True if waveform meets length and return-to-threshold requirements."""
    if waveform.size != n_samples_per_waveform:
        return False
    elif threshold_return is None:
        return True
    else:
        return np.any(waveform[center_index:] * direction <= threshold_return * direction)
