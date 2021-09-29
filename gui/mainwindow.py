import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph import ViewBox
from gui.cluster_list_model import ClusterListModel


class MainWindow(QMainWindow):
    toolbar: QToolBar
    viewMenu: QMenu
    waveformPlot: pg.PlotItem
    xyFeaturesPlot: pg.PlotItem
    xzFeaturesPlot: pg.PlotItem
    yzFeaturesPlot: pg.PlotItem
    clusterListView: QListView
    clusterListModel: ClusterListModel

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spike Sorting")
        self.toolbar = self._create_toolbar()
        self.viewMenu = self.menuBar().addMenu("&View")

        # Create layout for 3 plots (waveform, features xy, features xz, features yz)
        dock = QDockWidget("Waveform features")
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

        layoutWidget = QWidget(dock)
        layoutWidget.setLayout(layout)
        dock.setWidget(layoutWidget)
        dock.setAllowedAreas(Qt.AllDockWidgetAreas)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

        # Clusters
        dock = QDockWidget("Clusters", self)
        self.clusterListView, self.clusterListModel = self._create_cluster_list()
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setWidget(self.clusterListView)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.viewMenu.addAction(dock.toggleViewAction())

    def _create_toolbar(self):
        toolbar = self.addToolBar("File")
        style = self.style()
        toolbar.addAction(style.standardIcon(QStyle.SP_FileIcon), "New")
        toolbar.addAction(style.standardIcon(QStyle.SP_DialogOpenButton), "Open")
        toolbar.addAction(style.standardIcon(QStyle.SP_DialogSaveButton), "Save")
        toolbar.addAction("Select")
        toolbar.addAction("Merge")
        toolbar.addAction("Split")
        toolbar.addAction("Delete")
        return toolbar

    @staticmethod
    def _create_cluster_list() -> (QListView, ClusterListModel):
        view = QListView()
        view.setDragDropMode(QAbstractItemView.InternalMove)
        model = ClusterListModel(view)
        view.setModel(model)
        return view, model

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
