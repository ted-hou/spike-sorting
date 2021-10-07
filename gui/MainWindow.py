import sys
import typing

import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QModelIndex
import pyqtgraph as pg
from pyqtgraph import ViewBox
from gui.ClusterSelector import ClusterSelector
from gui.ChannelSelector import ChannelSelector
from spikedata import SpikeData
from spikefeatures import SpikeFeatures

# noinspection PyPep8Naming
class MainWindow(QMainWindow):
    spikeData: list[SpikeData]
    spikeFeatures: list[SpikeFeatures]

    toolbar: QToolBar
    viewMenu: QMenu
    waveformPlot: pg.PlotItem
    xyFeaturesPlot: pg.PlotItem
    xzFeaturesPlot: pg.PlotItem
    yzFeaturesPlot: pg.PlotItem
    channelSelector: ChannelSelector
    clusterSelector: ClusterSelector

    channelSelectorMaxWidth = 200

    def __init__(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray], parent: QWidget = None, flags: typing.Union[Qt.WindowFlags, Qt.WindowType] = Qt.WindowFlags()):
        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

        super().__init__(parent, flags)

        self.setWindowTitle("Spike Sorting")
        self.toolbar = self.createToolbar()
        self.viewMenu = self.menuBar().addMenu("&View")

        featuresWidget = self.createFeaturesWidget()
        self.setCentralWidget(featuresWidget)

        # ChannelSelector
        dock = QDockWidget("Channels", self)
        self.channelSelector = ChannelSelector([sd.channel for sd in spikeData], [sd.electrode for sd in spikeData], dock)
        dock.setWidget(self.channelSelector)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

        # ClusterSelector
        dock = QDockWidget("Clusters", self)
        self.clusterSelector = ClusterSelector(dock)
        self.clusterSelector.model().insertRows(0, spikeLabels[0].max() + 1)
        dock.setWidget(self.clusterSelector)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

        self.setDockOptions(QMainWindow.AllowNestedDocks)
        self.setTabPosition(Qt.AllDockWidgetAreas, QTabWidget.North)

    def load(self, spikeData: list[SpikeData], spikeFeatures: list[SpikeFeatures], spikeLabels: list[np.ndarray]):
        self.spikeData = spikeData
        self.spikeFeatures = spikeFeatures
        self.spikeLabels = spikeLabels

    def createToolbar(self):
        toolbar = self.addToolBar("File")
        style = self.style()
        toolbar.addAction(style.standardIcon(QStyle.SP_FileIcon), "New")
        toolbar.addAction(style.standardIcon(QStyle.SP_DialogOpenButton), "Open")
        toolbar.addAction(style.standardIcon(QStyle.SP_DialogSaveButton), "Save")
        return toolbar

    def createFeaturesWidget(self):
        # Create layout for 3 plots (waveform, features xy, features xz, features yz)
        # dock = QDockWidget("Waveform features", self)
        layout = QGridLayout()
        pw = pg.PlotWidget()
        self.waveformPlot = pw.getPlotItem()
        layout.addWidget(pw, 0, 1)
        pw = pg.PlotWidget()
        self.xyFeaturesPlot = pw.getPlotItem()
        layout.addWidget(pw, 0, 0)
        pw = pg.PlotWidget()
        self.xzFeaturesPlot = pw.getPlotItem()
        layout.addWidget(pw, 1, 0)
        pw = pg.PlotWidget()
        self.yzFeaturesPlot = pw.getPlotItem()
        layout.addWidget(pw, 1, 1)
        # Link x,y,z axes
        import weakref
        xyView = self.xyFeaturesPlot.getViewBox()
        xzView = self.xzFeaturesPlot.getViewBox()
        yzView = self.yzFeaturesPlot.getViewBox()
        from gui.pyqtgraph_utils import linkAxes
        linkAxes(xyView, yzView, ViewBox.YAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(xyView, xzView, ViewBox.XAxis, ViewBox.XAxis, reciprocal=True)
        linkAxes(yzView, xzView, ViewBox.YAxis, ViewBox.YAxis, reciprocal=True)
        layoutWidget = QWidget(self)
        layoutWidget.setLayout(layout)
        return layoutWidget

    @staticmethod
    def _create_plots():
        plt_waveform_raw = pg.PlotWidget()
        plt_waveform_mean = pg.PlotWidget()

        return plt_waveform_raw, plt_waveform_mean


def start_app():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    app.exec()
