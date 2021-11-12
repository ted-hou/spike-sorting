from PyQt6.QtGui import QPen, QKeyEvent, QKeySequence
from pyqtgraph.GraphicsScene.mouseEvents import MouseClickEvent
from PyQt6.QtCore import QPointF
from spikedata import SpikeData
from spikefeatures import SpikeFeatures
from .linkaxes import linkAxes
from .plot import *
from ..cluster.item import ClusterItem
from .roi import PolygonROI


# noinspection PyPep8Naming
class FeaturesPlot(QWidget):
    waveformPlot: pg.PlotItem
    xyPlot: pg.PlotItem
    xzPlot: pg.PlotItem
    yzPlot: pg.PlotItem
    plotItems: dict[ClusterItem, list[QGraphicsItem]]
    data: SpikeData = None
    features: SpikeFeatures = None
    roi: PolygonROI = None

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
        waveformWidget = pg.PlotWidget()
        self.waveformPlot = waveformWidget.getPlotItem()
        layout.addWidget(waveformWidget, 0, 1)
        xyWidget = pg.PlotWidget()
        self.xyPlot = xyWidget.getPlotItem()
        layout.addWidget(xyWidget, 0, 0)
        xzWidget = pg.PlotWidget()
        self.xzPlot = xzWidget.getPlotItem()
        layout.addWidget(xzWidget, 1, 0)
        yzWidget = pg.PlotWidget()
        self.yzPlot = yzWidget.getPlotItem()
        layout.addWidget(yzWidget, 1, 1)
        # Link x,y,z axes
        xyView = self.xyPlot.getViewBox()
        xzView = self.xzPlot.getViewBox()
        yzView = self.yzPlot.getViewBox()
        linkAxes(xyView, yzView, pg.ViewBox.YAxis, pg.ViewBox.XAxis, reciprocal=True)
        linkAxes(xyView, xzView, pg.ViewBox.XAxis, pg.ViewBox.XAxis, reciprocal=True)
        linkAxes(yzView, xzView, pg.ViewBox.YAxis, pg.ViewBox.YAxis, reciprocal=True)

        xyScene: pg.GraphicsScene = self.xyPlot.scene()
        xzScene: pg.GraphicsScene = self.xzPlot.scene()
        yzScene: pg.GraphicsScene = self.yzPlot.scene()

        xyScene.sigMouseClicked.connect(self.onPlotClicked)
        xzScene.sigMouseClicked.connect(self.onPlotClicked)
        yzScene.sigMouseClicked.connect(self.onPlotClicked)

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
                    pen = QGraphicsObject.data(item, DATA_PEN)
                    brush = QGraphicsObject.data(item, DATA_BRUSH)
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

    def onPlotClicked(self, ev: MouseClickEvent):
        # Ctrl+LClick -> make new ROI
        if self.roi is None and ev.button() == Qt.MouseButton.LeftButton and ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
            vb = ev.currentItem
            if not isinstance(vb, pg.ViewBox):
                vb = vb.getViewBox()
            self.roi = self.createROI(ev.scenePos(), vb)
            ev.accept()
        else:
            ev.ignore()

    def createROI(self, pos: pg.Point, vb: pg.ViewBox) -> PolygonROI:
        pen = QPen(QColor('Black'))
        roi = PolygonROI([vb.mapSceneToView(pos), vb.mapSceneToView(pos)], vb.scene(), pen=pen, handlePen=pen)
        vb.addItem(roi)
        roi.startDrawing()
        return roi

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key.Key_Return and self.roi is not None:
            self.roi.completeDrawing()

