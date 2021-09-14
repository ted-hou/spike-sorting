from time import time
import numpy as np
from continuousdata import BlackrockContinuousData
import spikedetect
from spikesorting import extract_features, cluster

file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy8\daisy8_20210708\daisy8_20210708.ns5 '
cont_data = BlackrockContinuousData()
cont_data.read(file, channels=(0, 1), n_samples=30000, electrodes=None)

spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0,
                                        n_sigmas_return=1.0)
spike_data = spike_data[0]

spike_features = extract_features(spike_data, ndims=5, method='haar')
labels = cluster(spike_features, n_clusters=3, method='kmeans')


from gui.plot import plot_waveforms
plot_waveforms(spike_data, labels=labels, mode='mean')
