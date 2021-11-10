from __future__ import annotations
import sys
import typing
import numpy as np
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from gui.ClusterSelector import ClusterSelector, ClusterTreeModel
from gui.ChannelSelector import ChannelSelector
from gui.FeaturesPlot import FeaturesPlot
from spikedata import SpikeData
from spikefeatures import SpikeFeatures


# noinspection PyPep8Naming
class MainWindow(QMainWindow):
    instance: MainWindow = None

    spikeData: list[SpikeData]
    spikeFeatures: list[SpikeFeatures]
    spikeLabels: list[np.ndarray]

    fileActions: dict[str, QAction]
    toolbar: QToolBar
    viewMenu: QMenu
    fileMenu: QMenu
    featuresPlot: FeaturesPlot
    channelSelector: ChannelSelector
    clusterSelector: ClusterSelector

    def __init__(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray], parent: QWidget = None):
        if MainWindow.instance is None:
            MainWindow.instance = self
        else:
            raise RuntimeError(f"At least one instance of MainWindow is already running.")

        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

        super().__init__(parent)

        self.setWindowTitle("Spike Sorting")
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
        # self.viewMenu.addAction(dock.toggleViewAction())

        # ClusterSelector
        dock = QDockWidget("Clusters", self)
        self.clusterSelector = ClusterSelector(dock)
        iChn = self.channelSelector.currentChannel
        self.clusterSelector.load(data=spikeData[iChn], features=spikeFeatures[iChn], labels=spikeLabels[iChn], seed=12345+iChn)
        dock.setWidget(self.clusterSelector)
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        # self.viewMenu.addAction(dock.toggleViewAction())

        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks)
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)

        # Set up connections
        # Handle channel change
        self.channelSelector.currentIndexChanged.connect(self.onChannelChanged)
        self.channelSelector.currentIndexChanged.emit(self.channelSelector.currentIndex)

        # Handle cluster color change
        model: ClusterTreeModel = self.clusterSelector.model()
        model.itemsRecolored.connect(self.featuresPlot.onColorChanged)
        model.itemsCheckStateChanged.connect(self.featuresPlot.onVisibilityChanged)
        model.itemsAdded.connect(self.featuresPlot.onClustersAdded)
        model.itemsRemoved.connect(self.featuresPlot.onClustersRemoved)

        # Menus
        self.fileActions = self.createActions()
        self.toolbar = self.createToolbar("File", self.fileActions.values())
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addActions(self.fileActions.values())
        self.editMenu: QMenu = self.menuBar().addMenu("&Edit")
        self.editMenu.addSeparator()
        self.editMenu.addActions(self.clusterSelector.clusterActions.values())
        self.editMenu.addSeparator()
        self.viewMenu = self.menuBar().addMenu("&View")

    def onChannelChanged(self, i: int):
        self.clusterSelector.load(data=self.spikeData[i], features=self.spikeFeatures[i], labels=self.spikeLabels[i], seed=12345+i)
        self.featuresPlot.clear()
        self.featuresPlot.load(self.spikeData[i], self.spikeFeatures[i])
        self.featuresPlot.plot(self.clusterSelector.model().rootItem.leaves())

    def load(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray]):
        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

    def createActions(self) -> dict[str, QAction]:
        style = self.style()

        newAction = QAction("New", self)
        newAction.setShortcut(QKeySequence.StandardKey.New)
        newAction.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        newAction.triggered.connect(lambda: print("New"))

        openAction = QAction("Open", self)
        openAction.setShortcut(QKeySequence.StandardKey.Open)
        openAction.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        openAction.triggered.connect(lambda: print("Open"))

        saveAction = QAction("Save", self)
        saveAction.setShortcut(QKeySequence.StandardKey.Save)
        saveAction.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        saveAction.triggered.connect(lambda: print("Save"))

        actions = {'new': newAction, 'open': openAction, 'save': saveAction}

        for action in actions.values():
            action.setToolTip(f"{action.text()} ({action.shortcut().toString()})")

        return actions

    def createToolbar(self, name, actions: typing.Iterable[QAction]):
        toolbar: QToolBar = self.addToolBar(name)
        toolbar.addActions(actions)
        return toolbar


def start_app():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
