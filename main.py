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
#
# import pyqtgraph as pg
#
# app = pg.mkQApp()
# w = pg.GraphicsLayoutWidget()
# w.show()
# p = w.addPlot()
#
#
#
# from gui.pyqtgraph_utils import PlotMultiCurveItem
# tic = pg.ptime.time()
# colors = 'rgbcmyk'
# for i_cluster in range(labels.max()):
#     waveforms_in_cluster = spike_data.waveforms[labels == i_cluster]
#     lines = PlotMultiCurveItem(x=np.tile(1000 * spike_data.waveform_timestamps, (waveforms_in_cluster.shape[0], 1)),
#                                y=waveforms_in_cluster, c=colors[i_cluster])
#     p.addItem(lines)
#
# p.setRange(xRange=(-.5, .5), yRange=(-500, 500))
# print(f"Plotted {spike_data.waveforms.shape[0]} traces in {pg.ptime.time() - tic:.3f} s.")
#
# app.exec_()

from gui.plot import plot_waveforms
plot_waveforms(spike_data, labels=labels)