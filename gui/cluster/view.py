from __future__ import annotations  # allows TreeItem type hint in its own constructor
from PyQt6.QtCore import QItemSelection
from PyQt6.QtGui import QContextMenuEvent, QAction, QKeySequence
from PyQt6.QtWidgets import *
from . import ClusterTreeModel

# noinspection PyPep8Naming
class ClusterSelector(QTreeView):
    clusterActions: dict[str, QAction]

    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.clusterActions = self.createActions()
        self.setModel(ClusterTreeModel(self))
        self.setHeaderHidden(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    def model(self) -> ClusterTreeModel:
        return super().model()

    def load(self, data, features, labels, seed: int = None):
        model: ClusterTreeModel = self.model()
        model.spikeData = data
        model.spikeFeatures = features
        from . import labelsToIndices
        model.loadIndices(labelsToIndices(labels), seed=seed)

    def createActions(self):
        mergeAction = QAction("Merge", self)
        mergeAction.triggered.connect(self.mergeSelected)
        mergeAction.setShortcut(QKeySequence('Ctrl+G'))
        self.addAction(mergeAction)

        splitAction = QAction("Split", self)
        splitAction.triggered.connect(self.splitSelected)
        splitAction.setShortcut(QKeySequence('Ctrl+F'))
        self.addAction(splitAction)

        clusterActions = {'merge': mergeAction, 'split': splitAction}
        return clusterActions

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addActions(self.clusterActions.values())
        menu.exec(event.globalPos())

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        super().selectionChanged(selected, deselected)
        if self.clusterActions is not None:
            self.clusterActions['merge'].setEnabled(ClusterTreeModel.canMerge(self.selectedIndexes()))
            self.clusterActions['split'].setEnabled(ClusterTreeModel.canSplit(self.selectedIndexes()))

    def mergeSelected(self):
        self.model().merge(self.selectedIndexes())

    def splitSelected(self):
        self.model().split(self.selectedIndexes())

