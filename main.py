import numpy as np
from continuousdata import BlackrockContinuousData, ContinuousData
import spikedetect
from spikefeatures import extract_features
from spikeclustering import cluster
from PyQt6.QtWidgets import QApplication
from gui import start_app

if __name__ == '__main__':
    # Read continuous data
    file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy9\daisy9_20211020\daisy9_20211020.ns5'
    cont_data = BlackrockContinuousData.fromfile(file, channels=(6, 11), n_samples=300000, packet_mode='last')

    # Or generate simulated data
    # cont_data = ContinuousData.generate(n_channels=5, sample_rate=30000, n_samples=30000*10, seed=42)

    # Spike detection
    spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0, n_sigmas_return=1.0)
    # del cont_data

    # Spike sorting
    spike_features = extract_features(spike_data, ndims=5, method='haar')
    spike_labels = cluster(spike_features, n_clusters=3, method='kmeans')

    app = start_app(spike_data, spike_features, spike_labels)
