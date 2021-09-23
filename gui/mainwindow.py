import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor, QFont
import pyqtgraph as pg
import gui


class MainWindow(QMainWindow):
    hToolBar: QToolBar
    hPltWaveformRaw: pg.PlotWidget
    hPltWaveformMean: pg.PlotWidget
    hListWidgetClusters: QListWidget

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spike Sorting")

        layout, layout_widget = self._create_layout()
        self.hListWidgetClusters = self._create_cluster_list()

        self.hToolBar = self._create_toolbar()
        self.hPltWaveformRaw, self.hPltWaveformMean = self._create_plots()

        layout.addWidget(self.hListWidgetClusters, 0, 0)
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

    def reassign_colors(self, disconnect=True, lw: QListWidget = None):
        if lw is None:
            lw = self.hListWidgetClusters
        if disconnect:
            self.enable_connections(False, lw=lw)

        for i in range(lw.count()):
            item = lw.item(i)
            font = item.font()
            if item.checkState() == Qt.Checked:
                item.setForeground(QColor('white'))
                item.setBackground(gui.default_color(i))
                font.setBold(True)
            else:
                item.setForeground(gui.default_color(i))
                item.setBackground(QColor('white'))
                font.setBold(False)
            item.setFont(font)

        if disconnect:
            self.enable_connections(True, lw=lw)

    def enable_connections(self, enable=True, lw: QListWidget = None):
        if lw is None:
            lw = self.hListWidgetClusters
        if enable:
            lw.itemChanged.connect(lambda: self.reassign_colors(True, lw=lw))
            lw.model().rowsMoved.connect(lambda: self.reassign_colors(True, lw=lw))
        else:
            lw.itemChanged.disconnect()
            lw.model().rowsMoved.disconnect()

    def _create_cluster_list(self):
        lw = QListWidget()
        lw.addItem("Asscracks")
        lw.addItem("Butts")
        lw.addItem("Boobies")
        lw.addItem("Poopoo")
        lw.addItem("Peepee")
        lw.addItem("Goop")
        lw.addItem("Nerp")
        for i in range(lw.count()):
            item = lw.item(i)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)

        lw.setDragDropMode(QAbstractItemView.InternalMove)
        lw.setDragEnabled(True)
        lw.setSelectionMode(QAbstractItemView.ExtendedSelection)

        self.reassign_colors(disconnect=False, lw=lw)
        self.enable_connections(True, lw=lw)
        return lw

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
