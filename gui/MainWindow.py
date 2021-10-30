import sys
import typing
import numpy as np
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from gui.ClusterSelector import ClusterSelector
from gui.ChannelSelector import ChannelSelector
from gui.FeaturesPlot import FeaturesPlot
from spikedata import SpikeData
from spikefeatures import SpikeFeatures


# noinspection PyPep8Naming
class MainWindow(QMainWindow):
    spikeData: list[SpikeData]
    spikeFeatures: list[SpikeFeatures]
    spikeLabels: list[np.ndarray]

    toolbar: QToolBar
    viewMenu: QMenu
    featuresPlot: FeaturesPlot
    channelSelector: ChannelSelector
    clusterSelector: ClusterSelector

    channelSelectorMaxWidth = 200

    def __init__(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray], parent: QWidget = None):
        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

        super().__init__(parent)

        self.setWindowTitle("Spike Sorting")
        self.toolbar = self.createToolbar()
        self.viewMenu = self.menuBar().addMenu("&View")

        self.featuresPlot = FeaturesPlot(self)
        self.setCentralWidget(self.featuresPlot)

        # ChannelSelector
        dock = QDockWidget("Channels", self)
        self.channelSelector = ChannelSelector(dock)
        self.channelSelector.load(spikeData)
        dock.setWidget(self.channelSelector)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

        # ClusterSelector
        dock = QDockWidget("Clusters", self)
        self.clusterSelector = ClusterSelector(dock)
        self.clusterSelector.load(spikeLabels[self.channelSelector.currentChannel])
        dock.setWidget(self.clusterSelector)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks)
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)

        # Set up connections
        # Handle channel change
        self.channelSelector.currentIndexChanged.connect(self.onChannelChanged)
        self.channelSelector.currentIndexChanged.emit(self.channelSelector.currentIndex)

        # Handle cluster visibility change
        # self.clusterSelector.itemCheckStateChanged.connect(self.featuresPlot.setClusterVisible)

        # Handle cluster index reordering
        # self.clusterSelector.itemsMoved.connect(self.onClusterMoved)

    def onChannelChanged(self, i: int):
        self.clusterSelector.load(self.spikeLabels[i])
        self.featuresPlot.plot(self.spikeData[i], self.spikeFeatures[i], self.spikeLabels[i])

    def onClusterMoved(self, source: int, count: int, destination: int):
        from spikesorting import move_clusters
        i = self.channelSelector.currentIndex
        move_clusters(self.spikeLabels[i], source, count, destination, in_place=True)
        self.featuresPlot.reorder(moveSource=source, moveCount=count, moveDestination=destination)

    def load(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray]):
        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

    def createToolbar(self):
        toolbar = self.addToolBar("File")
        style = self.style()
        toolbar.addAction(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon), "New")
        toolbar.addAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton), "Open")
        toolbar.addAction(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton), "Save")
        return toolbar


def start_app():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
