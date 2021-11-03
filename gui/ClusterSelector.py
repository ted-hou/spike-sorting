from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
import numpy as np
from PyQt6.QtCore import Qt, QModelIndex, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal, \
    QAbstractItemModel, QObject, QItemSelection
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import *
import gui
from abc import ABC, abstractmethod


# noinspection PyPep8Naming
class ClusterItem(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def indices(self) -> np.ndarray:
        ...

    @property
    @abstractmethod
    def color(self) -> QColor:
        ...

    @property
    @abstractmethod
    def visible(self) -> bool:
        ...

    plotItems = None

    def onColorChanged(self, color: QColor):
        from gui.FeaturesPlot import FeaturesPlot
        if self.plotItems is not None:
            FeaturesPlot.setClusterColor(self.plotItems, color)

    def onVisibilityChanged(self, visible: bool):
        from gui.FeaturesPlot import FeaturesPlot
        if self.plotItems is not None:
            FeaturesPlot.setClusterVisible(self.plotItems, visible)


# noinspection PyPep8Naming
class ClusterTreeItem(ClusterItem):
    """
    Tree item containing a parent TreeItem reference, a list of children TreeItems, and its own data as a QVariant
    """

    _children: list[ClusterTreeItem]
    _parent: ClusterTreeItem | None
    _name: str = ''
    _checkState: Qt.CheckState = Qt.CheckState.Checked
    _indices: np.ndarray | None
    _cachedIndices: np.ndarray | None
    _dirty: bool
    _colorRange: gui.ColorRange

    def __init__(self, name: str, indices: np.ndarray = None, colorRange: gui.ColorRange = None):
        super().__init__()
        self._name = name
        self._checkState = Qt.CheckState.Checked
        self._children = []
        self._parent = None
        self._indices = indices
        self._cachedIndices = None
        self._dirty = True
        if colorRange is None:
            self._colorRange = gui.ColorRange()

    # Ported from C++, might not be necessary in python because GC
    def __del__(self):
        self._children.clear()

    def isValid(self):
        return self.childCount() > 0 or self._indices is not None

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def indices(self):
        """Absolute waveform indices associated with this cluster. If this is a parent item, returns combined indices
        of all (deep) child items. """
        if self.childCount() == 0:
            return self._indices
        else:
            # Recombine indices from children if marked dirty
            if self.dirty:
                size = self.size()
                self._cachedIndices = np.empty((size,), dtype=np.uint32)
                i = 0
                for child in self._children:
                    childIndices = child.indices
                    self._cachedIndices[i:i + childIndices.size] = childIndices
                    i += childIndices.size
                self.dirty = False
            return self._cachedIndices

    @indices.setter
    def indices(self, value: np.ndarray):
        self._indices = value

    @property
    def dirty(self) -> bool:
        """True if indices needs updating. This is flagged when a child item is added or removed"""
        return self._dirty or any([child.dirty for child in self._children])

    @dirty.setter
    def dirty(self, value: bool):
        self._dirty = value

    def size(self) -> int:
        if self.childCount() == 0:
            return self._indices.size
        else:
            count = 0
            for child in self._children:
                count += child.size()
            return count

    @property
    def visible(self) -> bool:
        return self.checkState == Qt.CheckState.Checked

    @property
    def checkState(self):
        return self._checkState

    @checkState.setter
    def checkState(self, value: Qt.CheckState):
        if isinstance(value, int):
            value = Qt.CheckState(value)
        self._checkState = value
        # Notify parents, recursively, until we hit root
        parent = self.parent
        while parent is not None:
            if value is not Qt.CheckState.PartiallyChecked and all(
                    [child.checkState == value for child in parent._children]):
                parent._checkState = value
            else:
                parent._checkState = Qt.CheckState.PartiallyChecked
            parent = parent.parent
        # Notify children
        for child in self._children:
            child.onParentCheckStateChanged(value)

        self.onVisibilityChanged(self.visible)

    def onParentCheckStateChanged(self, value: Qt.CheckState):
        if value is Qt.CheckState.Checked or value is Qt.CheckState.Unchecked:
            self._checkState = value
            self.onVisibilityChanged(self.visible)
            for child in self._children:
                child.onParentCheckStateChanged(value)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def color(self):
        if self.childCount() == 0:
            return self.colorRange.color
        else:
            return QColor(0, 0, 0)

    @property
    def colorRange(self):
        return self._colorRange

    @colorRange.setter
    def colorRange(self, value: gui.ColorRange):
        self._colorRange = value
        self.onColorChanged(self.color)

    def child(self, row: int) -> ClusterTreeItem | None:
        if row < 0 or row >= len(self._children):
            return None
        return self._children[row]

    def childCount(self) -> int:
        return len(self._children)

    def row(self) -> int:
        """Returns row number by searching in self.parent.children. Return 0 if parent is None"""
        if self._parent is not None:
            return self._parent._children.index(self)
        return 0

    def insertChildren(self, row: int, items: typing.Iterable[ClusterTreeItem]):
        if row < 0:
            raise ValueError(f"cannot insert, desired row index {row} is out of range [0, {len(self._children)}].")
        row = min(len(self._children), row)
        self._children[row:row] = items
        for item in items:
            item.parent = self
        self.indices = None
        self.dirty = True
        self.reassignColors()

    def removeChildren(self, row: int, count: int):
        for c in self._children[row:row + count]:
            c.parent = None
        del self._children[row:row + count]
        self.indices = None
        self.dirty = True
        # self.reassignColors()

    def popChildren(self, row: int, count) -> list[ClusterTreeItem]:
        items = self._children[row:row + count]
        self.removeChildren(row, count)
        return items

    def insertChild(self, row: int, item: ClusterTreeItem):
        self.insertChildren(row, [item])

    def appendChild(self, item: ClusterTreeItem):
        self.insertChild(self.childCount(), item)
        item.parent = self
        self.dirty = True

    def removeChild(self, row: int):
        self.removeChildren(row, 1)

    def popChild(self, row: int) -> ClusterTreeItem:
        return self.popChildren(row, 1)[0]

    def reassignColors(self):
        childCount = self.childCount()
        if childCount > 0:
            colorRanges = self.colorRange.split(childCount, 'hue')
            for i in range(childCount):
                child = self.child(i)
                child.colorRange = colorRanges[i]
                child.reassignColors()

    def copy(self) -> ClusterTreeItem:
        """Return a childless shallow copy of the item"""
        obj = ClusterTreeItem(self._name, self._indices)
        obj._checkState = self._checkState
        obj.plotItems = self.plotItems
        return obj

    def leaves(self) -> list[ClusterTreeItem]:
        """Return a list containing all leaf nodes in the tree."""
        items = []
        for child in self._children:
            if child.childCount() == 0 and child._indices is not None:
                items.append(child)
            elif child.childCount() > 0:
                items.extend(child.leaves())
        return items


# noinspection PyPep8Naming
class ClusterTreeModel(QAbstractItemModel):
    rootItem: ClusterTreeItem
    _mimeType = "application/vnd.text.list"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.rootItem = ClusterTreeItem('Root')

    def __del__(self):
        del self.rootItem

    def loadFromIndices(self, indices: list):
        self.beginResetModel()
        del self.rootItem
        self.rootItem = self.itemFromIndices('Root', indices)
        self.endResetModel()

    def itemFromIndices(self, name: str, indices: list) -> ClusterTreeItem:
        if len(indices) == 1 and isinstance(indices[0], list):
            return ClusterTreeItem(name, indices[0])

        item = ClusterTreeItem(name)
        for i in range(len(indices)):
            if isinstance(indices[i], np.ndarray):
                childItem = ClusterTreeItem(gui.randomNames()[0], indices[i])
            else:
                childItem = self.itemFromIndices(gui.randomNames()[0], indices[i])
            item.appendChild(childItem)
        return item

    def index(self, row: int, column: int, parent: QModelIndex = None) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent is not None and parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.rootItem

        childItem = parentItem.child(row)
        if childItem is not None:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index: QModelIndex = None) -> QModelIndex:
        if index is None or not index.isValid():
            return QModelIndex()

        childItem: ClusterTreeItem = index.internalPointer()
        if not isinstance(childItem, ClusterTreeItem):
            return QModelIndex()
        parentItem = childItem.parent

        # Top-level items do not have a valid parent index
        if parentItem is self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent: QModelIndex = None) -> int:
        if parent is not None:
            if parent.column() > 0:
                return 0
            elif parent.isValid():
                parentItem = parent.internalPointer()
            else:
                parentItem = self.rootItem
        else:
            parentItem = self.rootItem

        return parentItem.childCount()

    def columnCount(self, parent: QModelIndex = None) -> int:
        return 1

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = None):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.rootItem.name
        return QVariant()

    def data(self, index: QModelIndex, role=None):
        if index is None or not index.isValid():
            return QVariant()

        item: ClusterTreeItem = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            return item.name
            # return f"{item.row() + 1} - {item.name}"
        elif role == Qt.ItemDataRole.ToolTipRole:
            return f"{item.indices.size}"
        elif role == Qt.ItemDataRole.CheckStateRole:
            return item.checkState
        elif role == Qt.ItemDataRole.UserRole:
            return item.indices
        # elif role == Qt.ItemDataRole.FontRole:
        #     return
        elif role == Qt.ItemDataRole.ForegroundRole:
            return item.color
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = None) -> bool:
        if index is None or not index.isValid():
            return False

        item: ClusterTreeItem = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole:
            item.name = value
            # Item
            self.dataChanged.emit(index, index, [role])
            return True
        elif role == Qt.ItemDataRole.CheckStateRole:
            item.checkState = value
            # Update parents, recursively to root:
            parentIndex = index
            while parentIndex.isValid():
                self.dataChanged.emit(parentIndex, parentIndex, [role])
                parentIndex = parentIndex.parent()
            # Update immediate children:
            self.dataChanged.emit(index.siblingAtRow(0), index.siblingAtRow(item.childCount()), [role])
            return True
        elif role == Qt.ItemDataRole.UserRole:
            item.indices = value
            self.dataChanged.emit(index, index, [role])
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        baseFlags = QAbstractItemModel.flags(self, index)
        if not index.isValid():
            return baseFlags | Qt.ItemFlag.ItemIsDropEnabled
        else:
            return baseFlags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    # Drag and drop
    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [self._mimeType]

    def mimeData(self, indexes: typing.Iterable[QModelIndex]) -> QMimeData:
        encodedData = QByteArray()
        stream = QDataStream(encodedData, QIODevice.OpenModeFlag.WriteOnly)

        # Get path to index
        for index in indexes:
            path = []
            parentIndex = index
            while parentIndex.isValid():
                path.insert(0, parentIndex.row())
                parentIndex = parentIndex.parent()
            stream.writeUInt8(len(path))
            for i in path:
                stream.writeUInt8(i)

        mimeData = QMimeData()
        mimeData.setData(self._mimeType, encodedData)
        return mimeData

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        """Verify tree structure - cannot move an item with its ancestor or offspring. Siblings, cousins, uncles, etc are okay."""
        if not data.hasFormat(self._mimeType):
            return False

        # Cannot move an item along with its ancestor or offspring
        paths = self._parseMimeData(data)
        for path in paths:
            path = path.copy()
            while len(path) > 0:
                del path[len(path) - 1]
                if path in paths:
                    return False

        # Cannot move an item onto its current parent
        if row == -1 and parent.isValid():
            for path in paths:
                parentIndex = self._pathToIndex(path).parent()
                if parentIndex == parent:
                    return False

        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) -> bool:
        if action == Qt.DropAction.IgnoreAction:
            return True

        # Decode & sort data
        paths = self._parseMimeData(data)
        maxPathLength = max([len(p) for p in paths])

        def pathOrder(p: list[int]) -> int:
            value = 0
            for j in range(len(p)):
                value += 2 ** (8 * (maxPathLength - j - 1)) * p[j]
            return value

        paths.sort(key=pathOrder, reverse=True)

        # Remove and store all items in path
        items = []
        for path in paths:
            index = self._pathToIndex(path)
            i = index.row()
            parentIndex = self._pathToIndex(path[0:len(path) - 1])
            parentItem = parentIndex.internalPointer() if parentIndex.isValid() else self.rootItem
            self.beginRemoveRows(parentIndex, i, i)
            items.insert(0, parentItem.popChild(i))
            self.endRemoveRows()

        # Insert removed items into new position
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        if row == -1:
            row = parentItem.childCount()

        # If parentItem has no children, it will be copied into a child item
        if parentItem.childCount() == 0:
            items.insert(0, parentItem.copy())
            parentItem._indices = None
            parentItem.plotItems = None
        self.beginInsertRows(parent, row, row + len(items) - 1)
        parentItem.insertChildren(row, items)
        self.endInsertRows()

        self._removeInvalidChildren()

        # Refresh CheckState (for visual update only)
        newIndices = [self.index(item.row(), 0, parent) for item in items]
        for i in range(len(newIndices)):
            self.setData(newIndices[i], items[i].checkState, Qt.ItemDataRole.CheckStateRole)

        return True

    def _pathToIndex(self, path: list[int]) -> QModelIndex:
        if len(path) == 0:
            return QModelIndex()
        index = QModelIndex()
        for p in path:
            index = self.index(p, 0, index)
        return index

    def _removeInvalidChildren(self, parentIndex: QModelIndex = QModelIndex()):
        """Recursively remove invalid ClusterTreeItem's from model."""
        i = 0
        parentItem = parentIndex.internalPointer() if parentIndex.isValid() else self.rootItem
        while parentItem.childCount() > i:
            childIndex = self.index(i, 0, parentIndex)
            self._removeInvalidChildren(childIndex)
            childItem = childIndex.internalPointer()
            if childItem.isValid():
                i += 1
            else:
                self.beginRemoveRows(parentIndex, i, i)
                parentItem.removeChild(i)
                self.endRemoveRows()

    @staticmethod
    def _indexToPath(index: QModelIndex) -> list[int]:
        if index is None or not index.isValid():
            return []
        path = [index.row()]
        while index.parent().isValid():
            index = index.parent()
            path.insert(0, index.row())
        return path

    def _parseMimeData(self, data: QMimeData) -> list[list[int]]:
        encodedData = data.data(self._mimeType)
        stream = QDataStream(encodedData, QIODevice.OpenModeFlag.ReadOnly)
        paths = []
        while not stream.atEnd():
            depth = stream.readUInt8()
            path = [stream.readUInt8() for _ in range(depth)]
            paths.append(path)
        return paths


# noinspection PyPep8Naming
class ClusterSelector(QTreeView):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setModel(ClusterTreeModel(self))
        self.setHeaderHidden(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    #
    # def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
    #     super().selectionChanged(selected, deselected)
    #     # print([i.row() for i in selected.indexes()], [i.row() for i in deselected.indexes()])

    def load(self, labels):
        indicesList = labelsToIndices(labels)
        self.model().loadFromIndices(indicesList)


# noinspection PyPep8Naming
def labelsToIndices(labels: np.ndarray) -> list[np.ndarray]:
    indices = []
    for i in np.unique(labels):
        indices.append(np.where(labels == i)[0])
    return indices


# noinspection PyPep8Naming
def indicesToLabels(indices: list[np.ndarray], out_labels: np.ndarray = None) -> np.ndarray:
    size = sum([np.size(i) for i in indices])
    if out_labels is None:
        out_labels = np.empty((size,), np.uint32)
    elif out_labels.shape != (size,):
        raise ValueError(f"out_labels {out_labels.shape} does not have desired shape ({size},)")

    for i in range(len(indices)):
        out_labels[indices[i]] = i

    return out_labels
