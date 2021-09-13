import numpy as np
import pyqtgraph as pg
from gui.pyqtgraph_utils import PlotMultiCurveItem
from spikedata import SpikeData


def plot_waveforms(spike_data: SpikeData, labels: np.ndarray = None):
    app = pg.mkQApp()
    w = pg.GraphicsLayoutWidget()
    w.show()
    p = w.addPlot()

    if labels is None:
        n_waveforms = spike_data.waveforms.shape[0]
        curves = PlotMultiCurveItem(x=np.tile(1000*spike_data.waveform_timestamps, reps=(n_waveforms, 1)),
                                    y=spike_data.waveforms,
                                    c='w')
        p.addItem(curves)
    else:
        colors = 'rgbcmyk'
        for i_cluster in range(np.max(labels)):
            waveforms = spike_data.waveforms[labels == i_cluster]
            n_waveforms = waveforms.shape[0]
            curves = PlotMultiCurveItem(x=np.tile(1000*spike_data.waveform_timestamps, reps=(n_waveforms, 1)),
                                        y=waveforms,
                                        c=colors[i_cluster])
            p.addItem(curves)

    p.setRange(xRange=(spike_data.waveform_timestamps.min() * 1000, spike_data.waveform_timestamps.max() * 1000))

    app.exec_()
