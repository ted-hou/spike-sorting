import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from pyqtgraph import ViewBox

from gui.pyqtgraph_utils import linkAxes
from gui.plot import *
from gui.ClusterSelector import ClusterItem


# noinspection PyPep8Naming
class FeaturesPlot(QWidget):
    waveformPlot: pg.PlotItem
    xyPlot: pg.PlotItem
    xzPlot: pg.PlotItem
    yzPlot: pg.PlotItem
    itemsPerCluster: list[list[QGraphicsItem]]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.createPlots()

    def createPlots(self):
        """Make child plot widgets in QGridLayout"""
        # Create layout for 3 plots (waveform, features xy, features xz, features yz)
        # dock = QDockWidget("Waveform features", self)
        layout = QGridLayout()
        pw = pg.PlotWidget()
        self.waveformPlot = pw.getPlotItem()
        layout.addWidget(pw, 0, 1)
        pw = pg.PlotWidget()
        self.xyPlot = pw.getPlotItem()
        layout.addWidget(pw, 0, 0)
        pw = pg.PlotWidget()
        self.xzPlot = pw.getPlotItem()
        layout.addWidget(pw, 1, 0)
        pw = pg.PlotWidget()
        self.yzPlot = pw.getPlotItem()
        layout.addWidget(pw, 1, 1)
        # Link x,y,z axes
        import weakref
        xyView = self.xyPlot.getViewBox()
        xzView = self.xzPlot.getViewBox()
        yzView = self.yzPlot.getViewBox()
        linkAxes(xyView, yzView, ViewBox.YAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(xyView, xzView, ViewBox.XAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(yzView, xzView, ViewBox.YAxis, ViewBox.YAxis, reciprocal=True)
        self.setLayout(layout)

    def plot(self, spikeData, spikeFeatures, spikeClusters: typing.Sequence[ClusterItem]):
        self.waveformPlot.clear()
        self.xyPlot.clear()
        self.xzPlot.clear()
        self.yzPlot.clear()

        indices = [sc.indices for sc in spikeClusters]
        colors = [sc.color for sc in spikeClusters]

        self.itemsPerCluster = []
        if spikeData is not None:
            _, waveformItems = plot_waveforms(spikeData, indices=indices, colors=colors, plt=self.waveformPlot, mode='mean')
            self.autoRange(features=False, waveforms=True)
            self.itemsPerCluster = waveformItems
        if spikeFeatures is not None:
            _, xyItems = plot_features(spikeFeatures, dims='xy', indices=indices, colors=colors, plt=self.xyPlot)
            _, xzItems = plot_features(spikeFeatures, dims='xz', indices=indices, colors=colors, plt=self.xzPlot)
            _, yzItems = plot_features(spikeFeatures, dims='yz', indices=indices, colors=colors, plt=self.yzPlot)
            self.autoRange(features=True, waveforms=False)
            if self.itemsPerCluster:
                for i in range(len(self.itemsPerCluster)):
                    self.itemsPerCluster[i].extend(xyItems[i])
            else:
                self.itemsPerCluster = xyItems
            for i in range(len(self.itemsPerCluster)):
                self.itemsPerCluster[i].extend(xzItems[i])
            for i in range(len(self.itemsPerCluster)):
                self.itemsPerCluster[i].extend(yzItems[i])

        # Set visibility
        if self.itemsPerCluster:
            for i in range(len(self.itemsPerCluster)):
                visibility = spikeClusters[i].visible
                for item in self.itemsPerCluster[i]:
                    item.setVisible(visibility)

        # Subscribe to color changes
        if self.itemsPerCluster:
            for i in range(len(self.itemsPerCluster)):
                spikeClusters[i].plotItems = self.itemsPerCluster[i]

    @staticmethod
    def setClusterVisible(items: typing.Iterable[QGraphicsItem], visible: bool):
        for item in items:
            item.setVisible(visible)

    @staticmethod
    def setClusterColor(items: typing.Iterable[QGraphicsItem], color: QColor):
        """Change color but keep alpha."""
        for item in items:
            pen: QPen = QGraphicsObject.data(item, DATA_PEN)
            brush: QBrush = QGraphicsObject.data(item, DATA_BRUSH)
            if pen is not None:
                color.setAlpha(pen.color().alpha())
                pen.setColor(color)
                item.setPen(pen)
            if brush is not None:
                color.setAlpha(brush.color().alpha())
                brush.setColor(color)
                item.setBrush(brush)

    def autoRange(self, features=True, waveforms=True):
        if features:
            self.xyPlot.autoRange()
            self.yzPlot.autoRange()
            self.xzPlot.autoRange()
        if waveforms:
            self.waveformPlot.autoRange()


