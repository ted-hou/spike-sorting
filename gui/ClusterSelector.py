from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
import numpy as np
from PyQt6.QtCore import Qt, QModelIndex, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal, \
    QAbstractItemModel, QObject, QItemSelection
from PyQt6.QtGui import QColor, QFont, QBrush, QContextMenuEvent, QAction
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

    def isLeaf(self) -> bool:
        return True

    def isBranch(self) -> bool:
        return False

    def __eq__(self, other):
        return self.name == other.name
        # return np.array_equal(self.indices, other.indices)

    def __hash__(self):
        return hash(self.name)
        # return hash(self.indices.tobytes())

    def __ne__(self, other):
        return not(self == other)


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

    def __init__(self, name: str, indices: np.ndarray = None, checkState: Qt.CheckState = Qt.CheckState.Checked, colorRange: gui.ColorRange = None):
        super().__init__()
        self._name = name
        self._checkState = checkState
        self._children = []
        self._parent = None
        self._indices = indices
        self._cachedIndices = None
        self._dirty = True
        self._colorRange = gui.ColorRange() if colorRange is None else colorRange

    @staticmethod
    def fromIndices(name: str, indices: list) -> ClusterTreeItem:
        if len(indices) == 1 and isinstance(indices[0], list):
            return ClusterTreeItem(name, indices[0])

        item = ClusterTreeItem(name)

        for i in range(len(indices)):
            if isinstance(indices[i], np.ndarray):
                childItem = ClusterTreeItem(f"{name}-{i + 1}", indices[i])
            else:
                childItem = ClusterTreeItem.fromIndices(f"{name}-{i + 1}", indices[i])
            item.insertChild(item.childCount(), childItem)
        return item

    def isValid(self) -> bool:
        """Either a branch node, or a leaf node with non-empty indices."""
        return self.childCount() > 0 or self._indices is not None

    def isLeaf(self):
        """A leaf node has no children."""
        return not self.isBranch()

    def isBranch(self):
        """A branch node has one or more children, but does not contain indices data directly."""
        return self.childCount() > 0

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

    def onParentCheckStateChanged(self, value: Qt.CheckState):
        if value is Qt.CheckState.Checked or value is Qt.CheckState.Unchecked:
            self._checkState = value
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

    def children(self):
        """Return a list of child items. This list is a copy of the internal list so it's safe to modify."""
        return self._children.copy()

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

    def removeChildren(self, row: int, count: int) -> typing.Sequence[ClusterTreeItem]:
        for c in self._children[row:row + count]:
            c.parent = None
        items = self._children[row:row + count]
        del self._children[row:row + count]
        self.indices = None
        self.dirty = True
        return items

    def insertChild(self, row: int, item: ClusterTreeItem):
        self.insertChildren(row, [item])

    def removeChild(self, row: int) -> ClusterTreeItem:
        return self.removeChildren(row, 1)[0]

    def copy(self) -> ClusterTreeItem:
        """Return a childless shallow copy of the item"""
        obj = ClusterTreeItem(name=self._name, indices=self._indices, checkState=self._checkState, colorRange=self.colorRange)
        return obj

    def leaves(self) -> list[ClusterTreeItem]:
        """Return all leaf nodes in the tree."""
        if self.isLeaf():
            return [self]
        else:
            items = []
            for child in self._children:
                if child.childCount() == 0 and child._indices is not None:
                    items.append(child)
                elif child.childCount() > 0:
                    items.extend(child.leaves())
            return items

    def branches(self) -> list[ClusterTreeItem]:
        """Return all branch nodes in the tree."""
        items = []
        if self.isBranch():
            items.append(self)
            for child in self._children:
                items.extend(child.branches())
        return items

    def traversal(self) -> list[ClusterTreeItem]:
        """Returns all items from a pre-order traversal of the tree."""
        items = [self]
        if len(self._children) > 0:
            for child in self._children:
                items.extend(child.traversal())
        return items

    @staticmethod
    def merge(items: list[ClusterTreeItem], name: str):
        # ensure items in list are direct descendents/ancestors of one another
        if ClusterTreeItem.containsDirectDescendants(items):
            raise ValueError(f"Cannot merge all {len(items)} items because list contains direct descendants.")

        # Convert branch nodes to leaf nodes
        leafItems = items.copy()
        for item in leafItems:
            if item.isBranch():
                leafItems.remove(item)
                leafItems.extend(item.leaves())

        # Pre-allocate and merge indices
        size = 0
        for item in leafItems:
            size += item.size()
        mergedIndices = np.empty((size,), dtype=np.uint32)
        i = 0
        for item in leafItems:
            mergedIndices[i:i+item.size()] = item.indices
            i += item.size()

        # Find the widest ColorRange among all items
        maxColorRange = max(items, key=lambda it: it.colorRange.width).colorRange

        mergedItem = ClusterTreeItem(name=name, indices=mergedIndices, checkState=Qt.CheckState.Checked, colorRange=maxColorRange)
        return mergedItem

    def split(self, data, method='kmeans', n=3) -> ClusterTreeItem:
        """
        Split an item into n subclusters.
        :param data: spike features (see spikesorting.cluster). Can be np.ndarray or SpikeFeatures
        :param method: clustering method, default 'kmeans'
        :param n: number of clusters
        :return: ClusterTreeItem containing all sub-clusters as child items
        """
        from spikesorting import cluster
        labels = cluster(data.features[self.indices, :], n_clusters=n, method=method)
        nSubClusters = labels.max(initial=-1) + 1

        indices = self.indices
        splitIndices = []
        for i in range(nSubClusters):
            splitIndices.append(indices[labels == i])

        item = ClusterTreeItem.fromIndices(f"{self.name}", splitIndices)
        item._colorRange = self._colorRange
        item._checkState = Qt.CheckState.Checked
        return item

    @staticmethod
    def containsDirectDescendants(items: typing.Iterable[ClusterTreeItem]):
        """Check if any item in the list is a direct descendant of another item in the list."""
        # We'll do this by checking if an item's parent, or grandparent, or great grandparent... are also in the list.
        for item in items:
            parent = item.parent
            while parent is not None:
                if parent in items:
                    return True
                parent = parent.parent
        return False


# noinspection PyPep8Naming
class ClusterTreeModel(QAbstractItemModel):
    from spikedata import SpikeData
    from spikefeatures import SpikeFeatures
    spikeData: SpikeData | None
    spikeFeatures: SpikeFeatures | None
    rootItem: ClusterTreeItem
    _mimeType = "application/vnd.text.list"

    # signals
    itemsAdded = pyqtSignal(list)
    itemsRemoved = pyqtSignal(list)
    itemsRecolored = pyqtSignal(list)
    itemsCheckStateChanged = pyqtSignal(list)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.rootItem = ClusterTreeItem('Root')
        self.spikeData = None
        self.spikeFeatures = None

    def __del__(self):
        del self.rootItem

    def loadIndices(self, indices: list, seed: int = None):
        self.beginResetModel()
        del self.rootItem
        self.rootItem = ClusterTreeItem.fromIndices('Root', indices)
        leaves = self.rootItem.leaves()
        leafNames = gui.randomNames(count=len(leaves), seed=seed)
        for i in range(len(leaves)):
            leaves[i].name = leafNames[i]
        self.recolorChildItems(self.rootItem)
        self.endResetModel()

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
            return item.name if item.isLeaf() else f"{item.name} (group)"
        elif role == Qt.ItemDataRole.EditRole:
            return item.name
        elif role == Qt.ItemDataRole.ToolTipRole:
            return f"{item.indices.size}"
        elif role == Qt.ItemDataRole.CheckStateRole:
            return item.checkState
        elif role == Qt.ItemDataRole.UserRole:
            return item.indices
        elif role == Qt.ItemDataRole.ForegroundRole:
            return item.color
        else:
            return QVariant()

    def setData(self, index: QModelIndex, value: typing.Any, role: int = None) -> bool:
        if index is None or not index.isValid():
            return False

        item: ClusterTreeItem = index.internalPointer()
        if role == Qt.ItemDataRole.DisplayRole | Qt.ItemDataRole.EditRole:
            item.name = value
            self.dataChanged.emit(index, index, [role])
            return True
        elif role == Qt.ItemDataRole.CheckStateRole:
            item.checkState = value
            self.itemsCheckStateChanged.emit(item.traversal())
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
            return baseFlags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable

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

    def _parseMimeData(self, data: QMimeData) -> list[list[int]]:
        encodedData = data.data(self._mimeType)
        stream = QDataStream(encodedData, QIODevice.OpenModeFlag.ReadOnly)
        paths = []
        while not stream.atEnd():
            depth = stream.readUInt8()
            path = [stream.readUInt8() for _ in range(depth)]
            paths.append(path)
        return paths

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int,
                        parent: QModelIndex) -> bool:
        """Verify tree structure - cannot move an item with its ancestor or descendent. Siblings, cousins, uncles, etc are okay."""
        if not data.hasFormat(self._mimeType):
            return False

        # Cannot move an item along with its ancestor or descendent
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
                parentIndex = self.pathToIndex(path).parent()
                if parentIndex == parent:
                    return False

        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) -> bool:
        if action == Qt.DropAction.IgnoreAction:
            return True

        # Decode & sort data
        paths = self._parseMimeData(data)
        ClusterTreeModel.sortPaths(paths)

        # Remove and store all items in path
        items = []
        for path in paths:
            index = self.pathToIndex(path)
            parentIndex = self.pathToIndex(path[0:len(path) - 1])
            removedItem = self.removeItem(index.row(), parentIndex)
            if removedItem is None:
                return False
            items.insert(0, removedItem)

        # Insert removed items into new position
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        if row == -1 or row > parentItem.childCount():
            row = parentItem.childCount()

        # If parentItem has no children, it will be copied into a child item
        if parentItem.childCount() == 0:
            items.insert(0, parentItem.copy())
            parentItem._indices = None
            parentItem.plotItems = None
            parentItem.name = "Group"
        if not self.insertItems(row, items, parent):
            return False

        self.removeInvalidChildren()
        self.recolorChildItems(self.rootItem)

        # Refresh CheckState (for visual update only)
        newIndices = [self.index(item.row(), 0, parent) for item in items]
        for i in range(len(newIndices)):
            self.setData(newIndices[i], items[i].checkState, Qt.ItemDataRole.CheckStateRole)

        return True

    def insertItems(self, row: int, items: typing.Sequence[ClusterTreeItem], parent: QModelIndex = QModelIndex()) -> bool:
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        # Fail if inserting at invalid index, or items is None or empty.
        childCount = parentItem.childCount()
        if row > childCount or row < 0 or items is None or not items:
            return False

        self.beginInsertRows(parent, row, row + len(items) - 1)
        parentItem.insertChildren(row, items)
        self.endInsertRows()

        # Signal the addition of this item, and all its children
        allItems = []
        [allItems.extend(item.traversal()) for item in items]
        self.itemsAdded.emit(allItems)

        return True

    def insertItem(self, row: int, item: ClusterTreeItem, parent: QModelIndex = QModelIndex()) -> bool:
        return self.insertItems(row, [item], parent)

    def removeItems(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> typing.Sequence[ClusterTreeItem] | None:
        """Remove and return a list of removed items. Returns None if invalid arguments were provided."""
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        # Fail if removing invalid index range.
        if count <= 0 or row < 0 or row + count > parentItem.childCount():
            return None

        self.beginRemoveRows(parent, row, row + count - 1)
        items = parentItem.removeChildren(row, count)
        self.endRemoveRows()

        # Signal the removal of this item and all its children
        allItems = []
        [allItems.extend(item.traversal()) for item in items]
        self.itemsRemoved.emit(allItems)

        return items

    def removeItem(self, row: int, parent: QModelIndex = QModelIndex()) -> ClusterTreeItem | None:
        """Remove and return removed item. Returns None if invalid arguments were provided."""
        items = self.removeItems(row, 1, parent)
        if items is None:
            return None
        else:
            return items[0]

    def recolorChildItems(self, item: ClusterTreeItem = None):
        """Reassign colors for an item's descendants."""

        if item is None:
            item = self.rootItem

        childCount = item.childCount()
        if childCount > 0:
            colorRanges = item.colorRange.split(childCount, 'hue')
            for i in range(childCount):
                child = item.child(i)
                child.colorRange = colorRanges[i]
                self.recolorChildItems(child)
            self.itemsRecolored.emit(item.children())

    def removeInvalidChildren(self, parentIndex: QModelIndex = QModelIndex()):
        """Recursively remove invalid ClusterTreeItem's from model."""
        i = 0
        parentItem = parentIndex.internalPointer() if parentIndex.isValid() else self.rootItem
        while parentItem.childCount() > i:
            childIndex = self.index(i, 0, parentIndex)
            self.removeInvalidChildren(childIndex)
            childItem = childIndex.internalPointer()
            if childItem.isValid():
                i += 1
            else:
                self.removeItem(i, parentIndex)

    def pathToIndex(self, path: list[int]) -> QModelIndex:
        if len(path) == 0:
            return QModelIndex()
        index = QModelIndex()
        for p in path:
            index = self.index(p, 0, index)
        return index

    @staticmethod
    def indexToPath(index: QModelIndex) -> list[int]:
        if index is None or not index.isValid():
            return []
        path = [index.row()]
        while index.parent().isValid():
            index = index.parent()
            path.insert(0, index.row())
        return path

    @staticmethod
    def indexDepth(index: QModelIndex) -> int:
        if index is None or not index.isValid():
            return 0
        depth = 0
        index = index.parent()
        while index.isValid():
            depth += 1
            index = index.parent()
        return depth

    @staticmethod
    def pathOrder(path: typing.Sequence[int], maxDepth: int):
        value = 0
        for j in range(len(path)):
            value += 2 ** (8 * (maxDepth - j - 1)) * path[j]
        return value

    @staticmethod
    def sortPaths(paths: list[list[int]], reverse=True):
        """Sort paths from bottom of tree to top of tree."""

        maxDepth = max([len(p) for p in paths])

        paths.sort(key=lambda path: ClusterTreeModel.pathOrder(path, maxDepth), reverse=reverse)

    @staticmethod
    def sortIndices(indices: list[QModelIndex], reverse=True):
        maxDepth = max([ClusterTreeModel.indexDepth(index) for index in indices])
        indices.sort(key=lambda index: ClusterTreeModel.pathOrder(ClusterTreeModel.indexToPath(index), maxDepth), reverse=reverse)

    @staticmethod
    def canMerge(indices: typing.Sequence[QModelIndex]) -> bool:
        if len(indices) <= 1:
            return False

        # Check if list contains direct descendants of any other item in list
        for index in indices:
            parentIndex = index.parent()
            while parentIndex.isValid():
                if parentIndex in indices:
                    return False
                parentIndex = parentIndex.parent()
        return True

    def merge(self, indices: list[QModelIndex]) -> bool:
        """Merge indices in list, and replace the shallowest item with the merged item. If a branch item is listed, all its leaves will be merged."""
        if not ClusterTreeModel.canMerge(indices):
            return False

        # Sort indices from bottom to top
        indices = indices.copy()
        ClusterTreeModel.sortIndices(indices, reverse=True)

        # Find shallowest index, this will be replaced by the merged index
        shallowestIndex = indices[-1]
        targetParentIndex = shallowestIndex.parent()
        targetRow = shallowestIndex.row()

        # Generate merged item
        mergedItems = ClusterTreeItem.merge([index.internalPointer() for index in indices], name='+'.join([idx.internalPointer().name for idx in indices][::-1]))#, name=shallowestIndex.internalPointer().name)

        # Remove merged items
        for index in indices:
            parentIndex = index.parent()
            row = index.row()
            if self.removeItem(row, parentIndex) is None:
                raise RuntimeError(f"Failed to remove item at row {row} for parent path {self.indexToPath(parentIndex)}")

        # Insert merged item
        if not self.insertItem(targetRow, mergedItems, targetParentIndex):
            raise RuntimeError(f"Failed to insert item at row {targetRow} for parent path {self.indexToPath(targetParentIndex)}")

        # Remove invalid children
        self.removeInvalidChildren()
        self.recolorChildItems(self.rootItem)
        return True

    @staticmethod
    def canSplit(indices: list[QModelIndex]) -> bool:
        """Only non-root, leaf nodes can be split."""
        return all([index.isValid() and index.internalPointer().isLeaf() for index in indices])

    def split(self, indices: list[QModelIndex], method='kmeans', n=3) -> bool:
        """Split each item into a specified number of sub-clusters."""
        if not ClusterTreeModel.canSplit(indices):
            return False

        for index in indices:
            item: ClusterTreeItem = index.internalPointer()
            row = item.row()
            parentIndex = index.parent()
            newItem = item.split(self.spikeFeatures, method=method, n=n)
            self.removeItem(row, parentIndex)
            self.insertItem(row, newItem, parentIndex)
            self.recolorChildItems(newItem)
            # newIndex = self.index(row, 0, parentIndex)
            # self.beginInsertRows(newIndex, 0, newItem.childCount() - 1)
            # self.endInsertRows()

        return True


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

        self.mergeAction, self.splitAction = self.createContextMenuActions()

    # def selectionChanged(self, selected: QItemSelection, deselected: QItemSelection) -> None:
    #     super().selectionChanged(selected, deselected)
    #     # print([i.row() for i in selected.indexes()], [i.row() for i in deselected.indexes()])

    def load(self, data, features, labels, seed: int = None):
        model: ClusterTreeModel = self.model()
        model.spikeData = data
        model.spikeFeatures = features
        model.loadIndices(labelsToIndices(labels), seed=seed)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        menu = QMenu(self)
        menu.addAction(self.mergeAction)
        menu.addAction(self.splitAction)
        self.mergeAction.setEnabled(ClusterTreeModel.canMerge(self.selectedIndexes()))
        self.splitAction.setEnabled(ClusterTreeModel.canSplit(self.selectedIndexes()))
        menu.exec(event.globalPos())

    def createContextMenuActions(self):
        mergeAction = QAction("Merge", self)
        mergeAction.triggered.connect(self.mergeSelected)

        splitAction = QAction("Split", self)
        splitAction.triggered.connect(self.splitSelected)

        return mergeAction, splitAction

    def mergeSelected(self):
        model: ClusterTreeModel = self.model()
        model.merge(self.selectedIndexes())

    def splitSelected(self):
        model: ClusterTreeModel = self.model()
        model.split(self.selectedIndexes())


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
