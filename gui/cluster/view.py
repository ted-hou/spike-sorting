from __future__ import annotations  # allows TreeItem type hint in its own constructor
from PyQt6.QtCore import QItemSelection
from PyQt6.QtGui import QContextMenuEvent, QAction, QKeySequence
from PyQt6.QtWidgets import *
from .model import ClusterTreeModel


# noinspection PyPep8Naming
class ClusterSelector(QTreeView):
    clusterActions: dict[str, QAction]

    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.clusterActions = self.createActions()
        self.setModel(ClusterTreeModel(self))
        self.setHeaderHidden(False)
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
        mergeAction.setShortcut(QKeySequence('Ctrl+M'))
        self.addAction(mergeAction)

        splitAction = QAction("Split", self)
        splitAction.triggered.connect(self.splitSelected)
        splitAction.setShortcut(QKeySequence('Ctrl+F'))
        self.addAction(splitAction)

        unassignAction = QAction("Unassign", self)
        unassignAction.triggered.connect(self.unassignSelected)
        unassignAction.setShortcut(QKeySequence.StandardKey.Delete)
        self.addAction(unassignAction)

        restoreUnassignedAction = QAction("Restore unassigned", self)
        restoreUnassignedAction.triggered.connect(self.restoreUnassigned)
        self.addAction(restoreUnassignedAction)

        clusterActions = {'merge': mergeAction, 'split': splitAction, 'unassign': unassignAction, 'restoreUnassigned': restoreUnassignedAction}
        return clusterActions

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addActions(self.clusterActions.values())
        menu.exec(event.globalPos())

    def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        super().selectionChanged(selected, deselected)
        if self.clusterActions is not None:
            self.clusterActions['merge'].setEnabled(self.model().canMerge(self.selectedIndexes()))
            self.clusterActions['split'].setEnabled(self.model().canSplit(self.selectedIndexes()))
            self.clusterActions['unassign'].setEnabled(self.model().canUnassign(self.selectedIndexes()))
            self.clusterActions['restoreUnassigned'].setEnabled(self.model().canRestoreUnassigned())

    def mergeSelected(self):
        self.model().merge(self.selectedIndexes())

    def splitSelected(self):
        self.model().split(self.selectedIndexes())

    def unassignSelected(self):
        self.model().unassign(self.selectedIndexes())

    def restoreUnassigned(self):
        self.model().restoreUnassigned()