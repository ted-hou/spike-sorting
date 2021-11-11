from pyqtgraph import ViewBox
from gui.features.pyqtgraph_utils import linkAxes
from gui.features.plot import *
from gui.cluster.item import ClusterItem
from spikedata import SpikeData
from spikefeatures import SpikeFeatures


# noinspection PyPep8Naming
class FeaturesPlot(QWidget):
    waveformPlot: pg.PlotItem
    xyPlot: pg.PlotItem
    xzPlot: pg.PlotItem
    yzPlot: pg.PlotItem
    plotItems: dict[ClusterItem, list[QGraphicsItem]]
    data: SpikeData = None
    features: SpikeFeatures = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plotItems = {}
        self.createPlots()

    def load(self, data: SpikeData, features: SpikeFeatures):
        self.data = data
        self.features = features

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
        xyView = self.xyPlot.getViewBox()
        xzView = self.xzPlot.getViewBox()
        yzView = self.yzPlot.getViewBox()
        linkAxes(xyView, yzView, ViewBox.YAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(xyView, xzView, ViewBox.XAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(yzView, xzView, ViewBox.YAxis, ViewBox.YAxis, reciprocal=True)
        self.setLayout(layout)

    def clear(self):
        self.waveformPlot.clear()
        self.xyPlot.clear()
        self.xzPlot.clear()
        self.yzPlot.clear()

    def plot(self, clusters: typing.Sequence[ClusterItem], data: SpikeData = None, features: SpikeFeatures = None):
        data = self.data if data is None else data
        features = self.features if features is None else features

        indices = [cluster.indices for cluster in clusters]
        colors = [cluster.color for cluster in clusters]

        # Make a list of lists (one per cluster) to append plot items to.
        plotItemsList = [self.plotItems[cluster] if cluster in self.plotItems else [] for cluster in clusters]

        if data is not None:
            _, waveformItems = plot_waveforms(data, indices=indices, colors=colors, plt=self.waveformPlot, mode='mean')
            self.autoRange(features=False, waveforms=True)
            for i in range(len(plotItemsList)):
                plotItemsList[i].extend(waveformItems[i])
            # self.plotItems.update(zip(spikeClusters, waveformItems))
        if features is not None:
            _, xyItems = plot_features(features, dims='xy', indices=indices, colors=colors, plt=self.xyPlot)
            _, xzItems = plot_features(features, dims='xz', indices=indices, colors=colors, plt=self.xzPlot)
            _, yzItems = plot_features(features, dims='yz', indices=indices, colors=colors, plt=self.yzPlot)
            self.autoRange(features=True, waveforms=False)
            for i in range(len(plotItemsList)):
                plotItemsList[i].extend(xyItems[i])
                plotItemsList[i].extend(xzItems[i])
                plotItemsList[i].extend(yzItems[i])

        # Store list to dictionary
        self.plotItems.update(zip(clusters, plotItemsList))

        # Set visibility
        self.onVisibilityChanged(clusters)

    def onVisibilityChanged(self, clusters: typing.Sequence[ClusterItem]):
        for cluster in clusters:
            if cluster in self.plotItems:
                for item in self.plotItems[cluster]:
                    item.setVisible(cluster.visible)

    def onColorChanged(self, clusters: typing.Sequence[ClusterItem]):
        """Change color but keep alpha."""
        for cluster in clusters:
            if cluster in self.plotItems:
                for item in self.plotItems[cluster]:
                    pen: QPen = QGraphicsObject.data(item, DATA_PEN)
                    brush: QBrush = QGraphicsObject.data(item, DATA_BRUSH)
                    color = cluster.color
                    if pen is not None:
                        color.setAlpha(pen.color().alpha())
                        pen.setColor(color)
                        item.setPen(pen)
                    if brush is not None:
                        color.setAlpha(brush.color().alpha())
                        brush.setColor(color)
                        item.setBrush(brush)

    def onClustersAdded(self, clusters: typing.Sequence[ClusterItem]):
        # Only plot leaf items if tree nodes are given
        clusters = [c for c in clusters if c.isLeaf()]
        # print(f'Adding to {len(clusters)} plot:', *[c.name for c in clusters])
        self.plot(clusters)

    def onClustersRemoved(self, clusters: typing.Sequence[ClusterItem]):
        # print(f'Removing {len(clusters)} from plot:', *[c.name for c in clusters])
        for cluster in clusters:
            if cluster in self.plotItems:
                for item in self.plotItems[cluster]:
                    self.waveformPlot.removeItem(item)
                    self.xyPlot.removeItem(item)
                    self.xzPlot.removeItem(item)
                    self.yzPlot.removeItem(item)
                del self.plotItems[cluster]

    def autoRange(self, features=True, waveforms=True):
        if features:
            self.xyPlot.autoRange()
            self.yzPlot.autoRange()
            self.xzPlot.autoRange()
        if waveforms:
            self.waveformPlot.autoRange()


