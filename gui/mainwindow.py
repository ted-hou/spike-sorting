import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from gui.cluster_list_model import ClusterListModel


class MainWindow(QMainWindow):
    hToolBar: QToolBar
    hPltWaveformRaw: pg.PlotWidget
    hPltWaveformMean: pg.PlotWidget
    hClusterListView: QListView
    hClusterListModel: ClusterListModel

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spike Sorting")

        layout, layout_widget = self._create_layout()
        self.hClusterListView, self.hClusterListModel = self._create_cluster_list()

        self.hToolBar = self._create_toolbar()
        self.hPltWaveformRaw, self.hPltWaveformMean = self._create_plots()

        layout.addWidget(self.hClusterListView, 0, 0)
        layout.addWidget(self.hPltWaveformRaw, 0, 1, alignment=Qt.AlignCenter)
        layout.addWidget(self.hPltWaveformMean, 0, 2, alignment=Qt.AlignCenter)

        self.show()

    def _create_layout(self):
        layout = QGridLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(25)
        w = QWidget(self)
        w.setLayout(layout)
        self.setCentralWidget(w)
        return layout, w

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
    def _create_cluster_list():
        view = QListView()
        view.setDragEnabled(True)
        view.setAcceptDrops(True)
        view.setDropIndicatorShown(True)
        view.setDragDropMode(QAbstractItemView.DragDrop)
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
