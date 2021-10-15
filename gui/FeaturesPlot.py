import pyqtgraph as pg
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import *
from pyqtgraph import ViewBox
from gui.pyqtgraph_utils import linkAxes
from gui.plot import *


# noinspection PyPep8Naming
class FeaturesPlot(QWidget):
    waveformPlot: pg.PlotItem
    xyPlot: pg.PlotItem
    xzPlot: pg.PlotItem
    yzPlot: pg.PlotItem
    itemsPerCluster: list[list[QGraphicsItem]]

    def __init__(self, parent=None, flags=Qt.WindowFlags()):
        super().__init__(parent, flags)
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

    def plot(self, spikeData, spikeFeatures, spikeLabels, clusterVisible=None):
        self.waveformPlot.clear()
        self.xyPlot.clear()
        self.xzPlot.clear()
        self.yzPlot.clear()

        self.itemsPerCluster = []
        if spikeData is not None:
            _, waveformItems = plot_waveforms(spikeData, labels=spikeLabels, plt=self.waveformPlot, mode='mean')
            self.autoRange(features=False, waveforms=True)
            self.itemsPerCluster = waveformItems
        if spikeFeatures is not None:
            _, xyItems = plot_features(spikeFeatures, dims='xy', labels=spikeLabels, plt=self.xyPlot)
            _, xzItems = plot_features(spikeFeatures, dims='xz', labels=spikeLabels, plt=self.xzPlot)
            _, yzItems = plot_features(spikeFeatures, dims='yz', labels=spikeLabels, plt=self.yzPlot)
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

        if clusterVisible is not None and self.itemsPerCluster:
            for i in range(len(self.itemsPerCluster)):
                self.setClusterVisible(i, clusterVisible[i])

    def setClusterVisible(self, index, visible=True):
        for item in self.itemsPerCluster[index]:
            item.setVisible(visible)

    def isClusterVisible(self, index):
        visible = True
        for item in self.itemsPerCluster[index]:
            visible = visible and item.isVisible()
        return visible

    def autoRange(self, features=True, waveforms=True):
        if features:
            self.xyPlot.autoRange()
            self.yzPlot.autoRange()
            self.xzPlot.autoRange()
        if waveforms:
            self.waveformPlot.autoRange()

    def reorder(self, from_index: int, to_index: int):
        """
        Reassign colors after moving a cluster index. Only RGB values are re-acquired from gui.default_colors().
        QBrush/QPen settings will be preserved. This is done by updating the stored QPen/QBrush objects.
        Requires the stored QGraphicsItem to have custom data attached via QGraphicsItem.setData() to work.

        :param from_index: old index of the cluster to be moved
        :param to_index: new index after a cluster was moved
        :return: None
        """
        # Reorder plot items so they appear in the new order
        ipc = self.itemsPerCluster
        ipc.insert(to_index, ipc.pop(from_index))

        # Re-assign colors
        for i in range(len(self.itemsPerCluster)):
            for item in self.itemsPerCluster[i]:
                pen: QPen = QGraphicsObject.data(item, DATA_PEN)
                brush: QBrush = QGraphicsObject.data(item, DATA_BRUSH)
                newColor = gui.default_color(i)
                if pen is not None:
                    color = pen.color()
                    newColor.setAlpha(color.alpha())
                    pen.setColor(newColor)
                    item.setPen(pen)
                if brush is not None:
                    color = brush.color()
                    newColor.setAlpha(color.alpha())
                    brush.setColor(newColor)
                    item.setBrush(brush)




