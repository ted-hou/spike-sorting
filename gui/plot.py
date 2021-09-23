import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets
import gui
from gui.pyqtgraph_utils import PlotMultiCurveItem
from spikedata import SpikeData

pg.setConfigOption('background', pg.mkColor(.9, .9, .9, .25))
pg.setConfigOption('foreground', 'k')


def plot_waveforms(spike_data: SpikeData, plt: pg.PlotWidget, labels: np.ndarray = None, mode='mean', yrange=None,
                   prct=5):
    """
    Plot waveforms from spike data.

    :param spike_data: SpikeData object
    :param plt: pyqtgraph.PlotWidget to plot in. (default None creates new widget)
    :param labels: (optional) cluster labels (0-N) for each waveform, each cluster is plotted in a different color
    :param mode: 'raw', 'mean', 'both'
    :param yrange: (min, max) or PlotWidget to copy range from
    :param prct: percentile (prct, 1-prct) to show in 'mean' mode. (0-50, default 5)
    :return:
    """
    app = _get_or_create_app()
    plt, layout, make_new_plot = _validate_or_create_plot(plt)
    plt.setLabels(left=spike_data.waveform_units, bottom='ms')

    if labels is None:
        waveforms = spike_data.waveforms * spike_data.waveform_conversion_factor
        _plot_waveforms(plt, waveforms, 1000 * spike_data.waveform_timestamps, color='k', mode=mode, prct=prct)
    else:
        for i_cluster in range(np.max(labels)):
            waveforms = spike_data.waveforms[labels == i_cluster] * spike_data.waveform_conversion_factor
            _plot_waveforms(plt, waveforms=waveforms, timestamps=1000 * spike_data.waveform_timestamps,
                            color=gui.default_color(i_cluster), mode=mode, prct=prct)

    # Set axis limits
    if isinstance(yrange, (tuple, list)):
        plt.setRange(xRange=[1000 * t for t in spike_data.detect_config.waveform_window],
                     yRange=yrange, padding=0)
    elif isinstance(yrange, pg.PlotWidget):
        plt.setRange(xRange=[1000 * t for t in spike_data.detect_config.waveform_window],
                     yRange=yrange.getPlotItem().viewRange()[1], padding=0)
    else:
        plt.setRange(xRange=[1000 * t for t in spike_data.detect_config.waveform_window],
                     padding=0)

    plt.disableAutoRange('xy')

    if make_new_plot:
        app.exec_()

    return plt


def _plot_waveforms(plt: pg.PlotItem, waveforms: np.ndarray, timestamps: np.ndarray, color='k',
                    mode='raw', prct=5):
    """Plot waveforms in one color."""
    if mode == 'raw':
        curves = PlotMultiCurveItem(x=np.tile(timestamps, reps=(waveforms.shape[0], 1)), y=waveforms,
                                    c=color)
        plt.addItem(curves)
        plt.setTitle('waveforms (raw)')
        return curves
    elif mode == 'mean':
        mean = waveforms.mean(axis=0)
        sd = waveforms.std(axis=0)
        prct_hi = np.percentile(waveforms, 100 - prct, axis=0)
        prct_lo = np.percentile(waveforms, prct, axis=0)

        color = pg.mkColor(color)
        mean_curve = pg.PlotCurveItem(x=timestamps, y=mean, pen=pg.mkPen(color, width=2, style=QtCore.Qt.SolidLine))
        color.setAlphaF(0.5)
        sd_pos_curve = pg.PlotCurveItem(x=timestamps, y=mean + sd,
                                        pen=pg.mkPen(color, width=1, style=QtCore.Qt.DotLine))
        sd_neg_curve = pg.PlotCurveItem(x=timestamps, y=mean - sd,
                                        pen=pg.mkPen(color, width=1, style=QtCore.Qt.DotLine))
        prct_hi_curve = pg.PlotCurveItem(x=timestamps, y=prct_hi,
                                         pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine))
        prct_lo_curve = pg.PlotCurveItem(x=timestamps, y=prct_lo,
                                         pen=pg.mkPen(color, width=1, style=QtCore.Qt.DashLine))
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
        plt.setTitle(f"waveforms (mean&#177;sd, {prct:d} - {100 - prct:d}% prct)")
        return mean_curve, sd_pos_curve, sd_neg_curve, prct_hi_curve, prct_lo_curve, sd_fill, prct_fill
    else:
        raise ValueError(f"Unrecognized plot mode '{mode}', expected 'raw', 'mean'")


def plot_features(spike_data: SpikeData, plt: pg.PlotWidget, labels: np.ndarray = None):
    app = _get_or_create_app()
    plt, layout, make_new_plot = _validate_or_create_plot()


def _get_or_create_app():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def _validate_or_create_plot(plt: pg.PlotWidget = None):
    make_new_plot = plt is None
    if make_new_plot:
        layout = pg.GraphicsLayoutWidget()
        layout.show()
        plt = layout.addPlot()
    else:
        layout = plt.parentWidget()
    return plt, layout, make_new_plot

