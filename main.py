from time import time
import numpy as np
from continuousdata import BlackrockContinuousData
import spikedetect
from spikesorting import extract_features, cluster
from gui.plot import plot_waveforms, plot_features

# Read continuous data
file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy9\daisy9_20211001\daisy9_20211001.ns5'
cont_data = BlackrockContinuousData()
cont_data.read(file, channels=range(32), n_samples=30000, electrodes=None)

# Spike detection
spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0,
                                        n_sigmas_return=1.0)
del cont_data

# Spike sorting
spike_features = extract_features(spike_data, ndims=5, method='haar')
spike_labels = cluster(spike_features, n_clusters=3, method='kmeans')
#
# # Plot waveforms
# # Create window and 2 subplots
# app = QtWidgets.QApplication([])
# w = QtWidgets.QWidget()
# layout = QtWidgets.QGridLayout()
# w.setLayout(layout)
# p1 = pg.PlotWidget()
# p2 = pg.PlotWidget()
# layout.addWidget(p1, 0, 0)
# layout.addWidget(p2, 0, 1)
#
# # Plot mean and raw waveforms
# plot_waveforms(spike_data, plt=p1, labels=labels, mode='raw')
# plot_waveforms(spike_data, plt=p2, labels=labels, mode='mean', y_range=p1)
#
# linear_roi = pg.LinearRegionItem(values=(-50.0, 50.0), orientation='horizontal', movable=True, bounds=p1.viewRange()[1])
# p1.addItem(linear_roi)
#
# line_roi = pg.InfiniteLine(pos=10, angle=0, movable=True, bounds=p2.viewRange()[1])
# p2.addItem(line_roi)

from PyQt5.QtWidgets import QApplication
from gui.MainWindow import MainWindow

app = QApplication([])
window = MainWindow(spike_data, spike_features, spike_labels)
# p1 = plot_waveforms(spike_data, labels=labels, plt=window.waveformPlot, mode='mean')
# p2 = plot_features(spike_features, dims='xy', labels=labels, plt=window.xyFeaturesPlot)
# p3 = plot_features(spike_features, dims='xz', labels=labels, plt=window.xzFeaturesPlot)
# p4 = plot_features(spike_features, dims='yz', labels=labels, plt=window.yzFeaturesPlot)
window.show()
app.exec()


from gui.MainWindow import start_app
# start_app()