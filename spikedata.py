import numpy as np
from spikedetect import SpikeDetectConfig


class SpikeData:
    """
    Contains spike data from a single channel.

    waveforms: np.ndarray with shape (n_waveforms, n_samples_per_waveform)
    """

    channel: int = None
    electrode: int = None
    sample_rate: float = None
    sample_indices: np.ndarray
    waveforms: np.ndarray  # (n_waveforms, n_samples_per_waveform)
    timestamps: np.ndarray
    waveform_timestamps: np.ndarray
    waveform_units: str = 'uV'
    waveform_conversion_factor: float = 1.0
    detect_config: SpikeDetectConfig

    def __init__(self, channel=None, sample_rate=None, electrode=None, sample_indices=None, waveforms=None,
                 timestamps=None, waveform_timestamps=None, waveform_units=None, waveform_conversion_factor=1.0,
                 detect_config=None):
        self.channel = channel
        self.sample_rate = sample_rate
        self.electrode = electrode
        self.sample_indices = sample_indices
        self.waveforms = waveforms
        self.timestamps = timestamps
        self.waveform_timestamps = waveform_timestamps
        self.waveform_units = waveform_units
        self.waveform_conversion_factor = waveform_conversion_factor
        self.detect_config = detect_config
