from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
import numpy as np
from PyQt6.QtCore import Qt, QModelIndex, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal, \
    QAbstractItemModel, QObject, QItemSelection
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import *
import gui


# noinspection PyPep8Naming
class ClusterTreeItemStyle:
    font: QFont
    fg: typing.Union[QColor, QBrush]
    bg: typing.Union[QColor, QBrush]
    _color: QColor
    _highlighted: bool = False

    def __init__(self, color: typing.Union[QColor, str], highlight=False):
        self.color = color
        self.font = QFont()
        self.highlighted = highlight

    @property
    def color(self) -> QColor:
        return self._color

    @color.setter
    def color(self, value: typing.Union[QColor, str]):
        if type(value) is str:
            value = QColor(value)
        if not isinstance(value, QColor):
            raise TypeError(f"color is type {type(value)}, expected QColor or str")
        self.bg = QColor('white')
        self.fg = value
        self.color = value

    @property
    def highlighted(self):
        return self._highlighted

    @highlighted.setter
    def highlighted(self, value: bool):
        self._highlighted = value
        self.font.setBold(value)


# noinspection PyPep8Naming
class ClusterTreeItem:
    """
    Tree item containing a parent TreeItem reference, a list of children TreeItems, and its own data as a QVariant
    """

    _children: list[ClusterTreeItem]
    _parent: ClusterTreeItem
    _name: str = ''
    _checkState: Qt.CheckState = Qt.CheckState.Checked
    _indices: np.ndarray | None
    _dirty: bool

    def __init__(self, name: str, indices: np.ndarray = None):
        self._name = name
        self._checkState = Qt.CheckState.Checked
        self._children = []
        self._indices = indices
        self._dirty = True

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
                self._indices = np.empty((size,), dtype=np.uint32)
                i = 0
                for child in self._children:
                    childIndices = child.indices
                    self._indices[i:i+childIndices.size] = childIndices
                    i += childIndices.size
            return self._indices

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

    def removeChildren(self, row: int, count: int):
        for c in self._children[row:row + count]:
            c.parent = None
        del self._children[row:row + count]
        self.indices = None
        self.dirty = True

    def popChildren(self, row: int, count) -> list[ClusterTreeItem]:
        items = self._children[row:row + count]
        self.removeChildren(row, count)
        self.indices = None
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

    def copy(self) -> ClusterTreeItem:
        """Return a childless shallow copy of the item"""
        obj = ClusterTreeItem(self._name, self._indices)
        obj._checkState = self._checkState
        return obj

    def removeInvalidChildren(self):
        i = 0
        while self.childCount() > i:
            self.child(i).removeInvalidChildren()
            if self.child(i).isValid():
                i += 1
            else:
                self.removeChild(i)

# noinspection PyPep8Naming
class ClusterTreeModel(QAbstractItemModel):
    rootItem: ClusterTreeItem
    _mimeType = "application/vnd.text.list"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.rootItem = ClusterTreeItem('Root')
        self.rootItem.appendChild(ClusterTreeItem("A"))
        self.rootItem.appendChild(ClusterTreeItem("B"))
        self.rootItem.child(0).appendChild(ClusterTreeItem("A-0", np.asarray([0, 2, 4, 6, 8], dtype=np.uint32)))
        self.rootItem.child(0).appendChild(ClusterTreeItem("A-1", np.asarray([1, 3, 5, 7, 9], dtype=np.uint32)))
        self.rootItem.child(1).appendChild(ClusterTreeItem("B-0", np.asarray([10, 12, 14, 16, 18], dtype=np.uint32)))
        self.rootItem.child(1).appendChild(ClusterTreeItem("B-1", np.asarray([11, 13, 15, 17, 19], dtype=np.uint32)))
        self.rootItem.child(1).appendChild(ClusterTreeItem("B-2"))
        self.rootItem.child(1).child(2).appendChild(ClusterTreeItem("B-2-0", np.asarray([20, 22, 24, 26, 28], dtype=np.uint32)))
        self.rootItem.child(1).child(2).appendChild(ClusterTreeItem("B-2-1", np.asarray([21, 23, 25, 27, 29], dtype=np.uint32)))

    def __del__(self):
        del self.rootItem

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
            return f"{item.row() + 1} - {item.name}"
        elif role == Qt.ItemDataRole.CheckStateRole:
            return item.checkState
        elif role == Qt.ItemDataRole.UserRole:
            return item.indices
        elif role == Qt.ItemDataRole.FontRole:
            return
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

    # # Inserting/removing rows
    # def insertRows(self, row: int, count: int, parent: QModelIndex = None) -> bool:
    #     # No parent specified, insert to root
    #     if parent is None:
    #         parent = QModelIndex()
    #
    #     self.beginInsertRows(parent, row, row + count - 1)
    #     parentItem: ClusterTreeItem = parent.internalPointer() if parent.isValid() else self.rootItem
    #     for i in range(row, row + count):
    #         parentItem.insertChild(i, ClusterTreeItem('__uninitialized__'))
    #     self.endInsertRows()
    #     return True
    #
    # def removeRows(self, row: int, count: int, parent: QModelIndex = None) -> bool:
    #     # No parent specified, remove from root
    #     if parent is None:
    #         parent = QModelIndex()
    #
    #     self.beginRemoveRows(parent, row, row + count - 1)
    #     parentItem: ClusterTreeItem = parent.internalPointer() if parent.isValid() else self.rootItem
    #     parentItem.removeChildren(row, count)
    #     self.endRemoveRows()
    #     return True
    #
    # def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex,
    #              destinationChild: int) -> bool:
    #     # When moving within the same parent, moveRows() is weird:
    #     # it expects destinationChild to be expectedNewIndex+count when moving downwards
    #     # it expects destinationChild to be expectedNewIndex when moving upwards
    #
    #     # Note that if sourceParent and destinationParent are the same, you must ensure that the destinationChild is not
    #     # within the range of sourceFirst and sourceLast + 1. You must also ensure that you do not attempt to move a row
    #     # to one of its own children or ancestors. This method returns false if either condition is true, in which case
    #     # you should abort your move operation.
    #     if not self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, destinationParent, destinationChild):
    #         return False
    #
    #     # When moving downwards within same parent, modify destination child
    #     if destinationParent is sourceParent and destinationChild > sourceRow:
    #         destinationChild -= count
    #
    #     sourceParentItem: ClusterTreeItem = sourceParent.internalPointer()
    #     destinationParentItem: ClusterTreeItem = destinationParent.internalPointer()
    #
    #     items = sourceParentItem.popChildren(sourceRow, count)
    #     destinationParentItem.insertChildren(destinationChild, items)
    #
    #     self.endMoveRows()
    #     return True

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

        paths = self._parseMimeData(data)
        for path in paths:
            path = path.copy()
            while len(path) > 0:
                del path[len(path) - 1]
                if path in paths:
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
            index = self._indexFromPath(path)
            row = index.row()
            parentIndex = self._indexFromPath(path[0:len(path) - 1])
            parentItem = parentIndex.internalPointer() if parentIndex.isValid() else self.rootItem
            self.beginRemoveRows(parentIndex, row, row)
            items.insert(0, parentItem.popChild(row))
            self.endRemoveRows()

        # Insert removed items into new position
        parentItem = parent.internalPointer() if parent.isValid() else self.rootItem
        if row == -1:
            row = parentItem.childCount()

        # If parentItem has no children, it will be copied into a child item
        if parentItem.childCount() == 0:
            items.insert(0, parentItem.copy())
        self.beginInsertRows(parent, row, row + len(items) - 1)
        parentItem.insertChildren(row, items)
        self.endInsertRows()

        self.rootItem.removeInvalidChildren()

        # Refresh CheckState (for visual update only)
        newIndices = [self.index(item.row(), 0, parent) for item in items]
        for i in range(len(newIndices)):
            self.setData(newIndices[i], items[i].checkState, Qt.ItemDataRole.CheckStateRole)

        return True

    def _indexFromPath(self, path: list[int]) -> QModelIndex:
        if len(path) == 0:
            return QModelIndex()
        index = QModelIndex()
        for p in path:
            index = self.index(p, 0, index)
        return index

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

    def load(self, labels, seed=None):
        pass
