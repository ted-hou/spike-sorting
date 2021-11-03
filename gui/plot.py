import typing
import numpy as np
import pyqtgraph as pg
# from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor, QBrush, QPen
import gui
from gui.pyqtgraph_utils import MultiCurvePlotItem
from spikedata import SpikeData
from spikefeatures import SpikeFeatures

pg.setConfigOption('background', pg.mkColor(.9, .9, .9, .25))
pg.setConfigOption('foreground', 'k')


DATA_PEN = 0
DATA_BRUSH = 1


def plot_waveforms(spike_data: SpikeData, plt: pg.PlotItem, labels: np.ndarray = None,
                   indices: list[np.ndarray] = None, colors: list[QColor] = None, mode='mean', yrange=None, prct=5):
    """
    Plot waveforms from spike data.

    :param spike_data: SpikeData object
    :param plt: pyqtgraph.PlotItem to plot in. (default None creates new widget)
    :param labels: (optional) cluster labels (0-N) for each waveform, each cluster is plotted in a different color
    :param mode: 'raw', 'mean', 'both'
    :param yrange: (min, max) or PlotWidget to copy range from
    :param prct: percentile (prct, 1-prct) to show in 'mean' mode. (0-50, default 5)
    :return:
    """
    app = _get_or_create_app()
    plt, layout, make_new_plot = _validate_or_create_plot(plt)
    plt.setLabel('left', text=f'amplitude ({spike_data.waveform_units})')
    plt.setLabel('bottom', text='time', units='s')

    if labels is None and indices is None:
        waveforms = spike_data.waveforms * spike_data.waveform_conversion_factor
        items = [_plot_waveforms(plt, waveforms, spike_data.waveform_timestamps, color='k', mode=mode, prct=prct)]
    elif labels is not None:
        items = []
        for i_cluster in range(np.max(labels)+1):
            waveforms = spike_data.waveforms[labels == i_cluster] * spike_data.waveform_conversion_factor
            itemsInCluster = _plot_waveforms(plt, waveforms=waveforms, timestamps=spike_data.waveform_timestamps,
                                             color=gui.default_color(i_cluster), mode=mode, prct=prct)
            items.append(itemsInCluster)
    elif indices is not None:
        items = []
        for i_cluster in range(len(indices)):
            waveforms = spike_data.waveforms[indices[i_cluster]] * spike_data.waveform_conversion_factor
            color = gui.default_color(i_cluster) if colors is None else colors[i_cluster]
            itemsInCluster = _plot_waveforms(plt, waveforms=waveforms, timestamps=spike_data.waveform_timestamps,
                                             color=color, mode=mode, prct=prct)
            items.append(itemsInCluster)

    # Set axis limits
    if isinstance(yrange, (tuple, list)):
        plt.setRange(xRange=[t for t in spike_data.detect_config.waveform_window],
                     yRange=yrange, padding=0.02)
    elif isinstance(yrange, pg.PlotWidget):
        plt.setXLink(yrange)
        plt.setYLink(yrange)
    else:
        plt.setRange(xRange=[t for t in spike_data.detect_config.waveform_window],
                     padding=0.02)
    xmin = spike_data.detect_config.waveform_window[0]
    xmax = spike_data.detect_config.waveform_window[1]

    plt.setLimits(xMin=xmin * 1.05, xMax=xmax * 1.05)
    plt.disableAutoRange('xy')
    plt.setMouseEnabled(x=False, y=False)
    plt.setMenuEnabled(False)
    plt.setAutoPan(x=False, y=False)

    if make_new_plot:
        app.exec_()

    return plt, items


def _plot_waveforms(plt: pg.PlotItem, waveforms: np.ndarray, timestamps: np.ndarray, color='k',
                    mode='raw', prct=5):
    """Plot waveforms in one color."""
    if mode == 'raw':
        curves = MultiCurvePlotItem(x=np.tile(timestamps, reps=(waveforms.shape[0], 1)), y=waveforms,
                                    c=color)
        plt.addItem(curves)
        # plt.setTitle('waveforms (raw)')
        return [curves]
    elif mode == 'mean':
        mean = waveforms.mean(axis=0)
        sd = waveforms.std(axis=0)
        prct_hi = np.percentile(waveforms, 100 - prct, axis=0)
        prct_lo = np.percentile(waveforms, prct, axis=0)

        color = pg.mkColor(color)
        pen = pg.mkPen(color, width=2, style=Qt.PenStyle.SolidLine)
        mean_curve = pg.PlotCurveItem(x=timestamps, y=mean, pen=pg.mkPen(color, width=2, style=Qt.PenStyle.SolidLine))
        QGraphicsItem.setData(mean_curve, DATA_PEN, pen)

        color.setAlphaF(0.5)
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DotLine)
        sd_pos_curve = pg.PlotCurveItem(x=timestamps, y=mean + sd, pen=pen)
        sd_neg_curve = pg.PlotCurveItem(x=timestamps, y=mean - sd, pen=pen)
        QGraphicsItem.setData(sd_pos_curve, DATA_PEN, pen)
        QGraphicsItem.setData(sd_neg_curve, DATA_PEN, pen)

        pen.setStyle(Qt.PenStyle.DashLine)
        prct_hi_curve = pg.PlotCurveItem(x=timestamps, y=prct_hi, pen=pen)
        prct_lo_curve = pg.PlotCurveItem(x=timestamps, y=prct_lo, pen=pen)
        QGraphicsItem.setData(prct_hi_curve, DATA_PEN, pen)
        QGraphicsItem.setData(prct_lo_curve, DATA_PEN, pen)

        color.setAlphaF(0.25)
        brush = pg.mkBrush(color)
        sd_fill = pg.FillBetweenItem(curve1=sd_pos_curve, curve2=sd_neg_curve, brush=brush)
        prct_fill = pg.FillBetweenItem(curve1=prct_hi_curve, curve2=prct_lo_curve, brush=brush)
        QGraphicsItem.setData(sd_fill, DATA_BRUSH, brush)
        QGraphicsItem.setData(prct_fill, DATA_BRUSH, brush)

        plt.addItem(mean_curve)
        plt.addItem(sd_pos_curve)
        plt.addItem(sd_neg_curve)
        plt.addItem(prct_hi_curve)
        plt.addItem(prct_lo_curve)
        plt.addItem(sd_fill)
        plt.addItem(prct_fill)
        # plt.setTitle(f"waveforms (mean&#177;sd, {prct:d} - {100 - prct:d}% prct)")
        return [mean_curve, sd_pos_curve, sd_neg_curve, prct_hi_curve, prct_lo_curve, sd_fill, prct_fill]
    else:
        raise ValueError(f"Unrecognized plot mode '{mode}', expected 'raw', 'mean'")


def plot_features(spike_features: SpikeFeatures, plt: pg.PlotItem, labels: np.ndarray = None,
                  indices: list[np.ndarray] = None, colors: list[QColor] = None,
                  dims: typing.Union[tuple, list, str] = 'xy'):
    app = _get_or_create_app()
    plt, layout, make_new_plot = _validate_or_create_plot(plt)

    if spike_features.ndims < 2:
        raise ValueError(f"Spike features must have at least 2 dimensions, but only {spike_features.ndims} were provided.")

    # Validate dims and convert to tuple (dim0, dim1)
    xlabel = None
    ylabel = None
    if type(dims) is str:
        if dims == 'xy':
            dims = (0, 1)
            xlabel = 'X'
            ylabel = 'Y'
        else:
            if spike_features.ndims < 3:
                raise ValueError(f"Spike features only has {spike_features.ndims} dimensions, 3 or more is needed for dims='{dims}'")
            if dims == 'xz':
                dims = (0, 2)
                xlabel = 'X'
                ylabel = 'Z'
            elif dims == 'yz':
                dims = (1, 2)
                xlabel = 'Y'
                ylabel = 'Z'
            else:
                raise ValueError(f"dims = '{dims}' not recognized, must be 'xy', 'xz', or 'yz'.")
    elif type(dims) is list or type(dims) is tuple:
        if len(dims) != 2:
            raise ValueError(f"dims has length {len(dims)}, expected list or tuple of length 2.")
        for i in range(2):
            if dims[i] >= spike_features.ndims or dims[i] < 0:
                raise ValueError(f"dims[{i}] = {dims[i]} exceeds feature space dimensions [0, {spike_features.ndims}]")

    items = []
    if labels is None and indices is None:
        features = spike_features.features[:, dims]
        color = pg.mkColor('k')
        scatter = pg.ScatterPlotItem(pos=features, pen=pg.mkPen(color), brush=pg.mkBrush(color), size=2)
        plt.addItem(scatter)
        items.append([scatter])
    elif labels is not None:
        for i_cluster in range(np.max(labels)+1):
            features = spike_features.features[labels == i_cluster, :][:, dims]
            color = gui.default_color(i_cluster)
            _plot_features_single_cluster(color, features, items, plt)
    elif indices is not None:
        for i_cluster in range(len(indices)):
            features = spike_features.features[indices[i_cluster], :][:, dims]
            color = colors[i_cluster]
            _plot_features_single_cluster(color, features, items, plt)

    plt.setLabel('bottom', xlabel)
    plt.setLabel('left', ylabel)

    if make_new_plot:
        app.exec_()

    return plt, items


def _plot_features_single_cluster(color, features, items, plt):
    pen = pg.mkPen(color)
    brush = pg.mkBrush(color)
    scatter = pg.ScatterPlotItem(pos=features, pen=pen, brush=brush, size=2)
    QGraphicsItem.setData(scatter, DATA_PEN, pen)
    QGraphicsItem.setData(scatter, DATA_BRUSH, brush)
    plt.addItem(scatter)
    items.append([scatter])


def _get_or_create_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _validate_or_create_plot(plt: pg.PlotItem = None):
    make_new_plot = plt is None
    if make_new_plot:
        layout = pg.GraphicsLayoutWidget()
        layout.show()
        plt = layout.addPlot()
    else:
        layout = plt.parentWidget()
    return plt, layout, make_new_plot

