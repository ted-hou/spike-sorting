from time import time
import numpy as np
from continuousdata import BlackrockContinuousData, ContinuousData
import spikedetect
from spikesorting import extract_features, cluster
from PyQt6.QtWidgets import QApplication
from gui.MainWindow import MainWindow

# Read continuous data
# file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy9\daisy9_20211001\daisy9_20211001.ns5'
# cont_data = BlackrockContinuousData()
# cont_data.read(file, channels=range(32), n_samples=30000, electrodes=None)

cont_data = ContinuousData.generate(n_channels=5, sample_rate=30000, n_samples=30000*10, seed=42)

# Spike detection
spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0,
                                        n_sigmas_return=1.0)
# del cont_data

# Spike sorting
spike_features = extract_features(spike_data, ndims=5, method='haar')
spike_labels = cluster(spike_features, n_clusters=3, method='kmeans')

app = QApplication([])
window = MainWindow(spike_data, spike_features, spike_labels)
window.show()
app.exec()
