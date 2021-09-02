import numpy as np
from spikedetect import SpikeDetectConfig


class SpikeData:
    """Contains spike data from a single channel."""

    channel: int = None
    electrode: int = None
    sample_rate: float = None
    sample_indices: np.ndarray
    waveforms: np.ndarray
    timestamps: np.ndarray
    waveform_timestamps: np.ndarray
    detect_config: SpikeDetectConfig

    def __init__(self, channel=None, sample_rate=None, electrode=None, sample_indices=None, waveforms=None, timestamps=None, waveform_timestamps=None, waveform_window=None, detect_config=None):
        self.channel = channel
        self.sample_rate = sample_rate
        self.electrode = electrode
        self.sample_indices = sample_indices
        self.waveforms = waveforms
        self.timestamps = timestamps
        self.waveform_timestamps = waveform_timestamps
        self.detect_config = detect_config

