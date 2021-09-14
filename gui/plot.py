import PyQt5.QtGui
import numpy as np
import pyqtgraph
import pyqtgraph as pg
from PyQt5 import QtCore
from gui.pyqtgraph_utils import PlotMultiCurveItem
from spikedata import SpikeData

pg.setConfigOption('background', 'w')  #pg.mkColor(.9, .9, .9, .25))
pg.setConfigOption('foreground', 'k')

def plot_waveforms(spike_data: SpikeData, labels: np.ndarray = None, mode='raw', y_range=None):
    """
    Plot waveforms from spike data.

    :param spike_data: SpikeData object
    :param labels: (optional) cluster labels (0-N) for each waveform, each cluster is plotted in a different color
    :param mode: 'raw', 'mean'
    :return:
    """
    app = pg.mkQApp()
    widget = pg.GraphicsLayoutWidget()
    widget.show()
    plt = widget.addPlot(left=spike_data.waveform_units, bottom='ms')

    if labels is None:
        waveforms = spike_data.waveforms * spike_data.waveform_conversion_factor
        _plot_waveforms(plt, waveforms, 1000*spike_data.waveform_timestamps, color='w', mode=mode)
    else:
        colors = (
            (230, 25, 25, 255),
            (25, 230, 25, 255),
            (25, 25, 230, 255),
            (230, 230, 25, 255),
        )
        for i_cluster in range(np.max(labels)):
            waveforms = spike_data.waveforms[labels == i_cluster] * spike_data.waveform_conversion_factor
            _plot_waveforms(plt, waveforms=waveforms,
                            timestamps=1000*spike_data.waveform_timestamps,
                            color=pg.mkColor(colors[i_cluster]), mode=mode)

    # Set axis limits
    plt.setRange(xRange=[1000*t for t in spike_data.detect_config.waveform_window], yRange=y_range)

    app.exec_()


def _plot_waveforms(plt: pg.PlotItem, waveforms: np.ndarray, timestamps: np.ndarray, color='w',
                    mode='raw', prct=5):
    """Plot waveforms in one color."""
    if mode == 'raw':
        curves = PlotMultiCurveItem(x=np.tile(timestamps, reps=(waveforms.shape[0], 1)), y=waveforms,
                                    c=color)
        plt.addItem(curves)
        return curves
    elif mode == 'mean':
        mean = waveforms.mean(axis=0)
        sd = waveforms.std(axis=0)
        prct_hi = np.percentile(waveforms, 100-prct, axis=0)
        prct_lo = np.percentile(waveforms, prct, axis=0)

        color = pg.mkColor(color)
        mean_curve = pg.PlotCurveItem(x=timestamps, y=mean, pen=pg.mkPen(color, width=2, style=QtCore.Qt.SolidLine))
        color.setAlphaF(0.5)
        sd_pos_curve = pg.PlotCurveItem(x=timestamps, y=mean + sd, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DotLine))
        sd_neg_curve = pg.PlotCurveItem(x=timestamps, y=mean - sd, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DotLine))
        prct_hi_curve = pg.PlotCurveItem(x=timestamps, y=prct_hi, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine))
        prct_lo_curve = pg.PlotCurveItem(x=timestamps, y=prct_lo, pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine))
        color.setAlphaF(0.25)
        sd_fill = pg.FillBetweenItem(curve1=sd_pos_curve, curve2=sd_neg_curve, brush=pg.mkBrush(color))
        prct_fill = pg.FillBetweenItem(curve1=prct_hi_curve, curve2=prct_lo_curve, brush=pg.mkBrush(color))

        plt.addItem(mean_curve)
        plt.addItem(sd_pos_curve)
        plt.addItem(sd_neg_curve)
        plt.addItem(prct_hi_curve)
        plt.addItem(prct_lo_curve)
        plt.addItem(sd_fill)
        plt.addItem(prct_fill)
        return mean_curve, sd_pos_curve, sd_neg_curve, prct_hi_curve, prct_lo_curve, sd_fill, prct_fill
    else:
        raise ValueError(f"Unrecognized plot mode '{mode}', expected 'raw', 'mean'")

