from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
from PyQt6.QtCore import QAbstractItemModel, pyqtSignal, QModelIndex, Qt, QVariant, QMimeData, QByteArray, QDataStream, \
    QIODevice
from PyQt6.QtWidgets import QWidget
from . import ClusterTreeItem


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
        from ..names import randomNames
        leafNames = randomNames(count=len(leaves), seed=seed)
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
            return f"{item.size}"
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

    def removeItems(self, row: int, count: int, parent: QModelIndex = QModelIndex()) -> typing.Sequence[
                                                                                            ClusterTreeItem] | None:
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