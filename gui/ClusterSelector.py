from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
import numpy as np
from PyQt6.QtCore import Qt, QModelIndex, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal, QAbstractItemModel, QObject
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

    def __init__(self, name: str, parent: ClusterTreeItem = None):
        self.parent = parent
        self._name = name
        self._checkState = Qt.CheckState.Checked
        self._children = []

    # Ported from C++, might not be necessary in python because GC
    def __del__(self):
        self._children.clear()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

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
            if value is not Qt.CheckState.PartiallyChecked and all([child.checkState == value for child in parent._children]):
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

    def appendChild(self, item: ClusterTreeItem):
        self._children.append(item)
        item.parent = self

    def insertChild(self, row: int, item: ClusterTreeItem):
        if row < 0 or row > len(self._children):
            raise ValueError(f"cannot insert, desired row index {row} is out of range [0, {len(self._children)}].")
        self._children.insert(row, item)
        item.parent = self

    def insertChildren(self, row: int, items: typing.Iterable[ClusterTreeItem]):
        if row < 0 or row > len(self._children):
            raise ValueError(f"cannot insert, desired row index {row} is out of range [0, {len(self._children)}].")
        self._children[row:row] = items
        for item in items:
            item.parent = self

    def removeChild(self, row: int):
        self._children[row].parent = None
        del self._children[row]

    def removeChildren(self, row: int, count: int):
        for c in self._children[row:row+count]:
            c.parent = None
        del self._children[row:row+count]

    def popChild(self, row: int) -> ClusterTreeItem:
        child = self._children.pop(row)
        child.parent = None
        return child

    def popChildren(self, row: int, count) -> list[ClusterTreeItem]:
        items = self._children[row:row+count]
        for item in items:
            item.parent = None
        del self._children[row:row+count]
        return items

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


# noinspection PyPep8Naming
class ClusterTreeModel(QAbstractItemModel):
    rootItem: ClusterTreeItem
    _mimeType = "application/vnd.text.list"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.rootItem = ClusterTreeItem('Root')
        self.rootItem.appendChild(ClusterTreeItem("A"))
        self.rootItem.appendChild(ClusterTreeItem("B"))
        self.rootItem.child(0).appendChild(ClusterTreeItem("A-1"))
        self.rootItem.child(0).appendChild(ClusterTreeItem("A-2"))

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
            self.broadcastDataChangeToChildren(index, [role])
            self.dataChanged.emit(index.siblingAtRow(0), index.siblingAtRow(item.childCount()), [role])
            return True
        else:
            return False

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        baseFlags = QAbstractItemModel.flags(self, index)
        if not index.isValid():
            return baseFlags | Qt.ItemFlag.ItemIsDropEnabled
        else:
            return baseFlags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    # Inserting/removing rows
    def insertRows(self, row: int, count: int, parent: QModelIndex = None) -> bool:
        # No parent specified, insert to root
        if parent is None or not parent.isValid():
            parent = self.rootItem

        self.beginInsertRows(parent, row, row + count - 1)
        parentItem: ClusterTreeItem = parent.internalPointer()
        for i in range(row, row + count):
            parentItem.insertChild(i, ClusterTreeItem('__uninitialized__'))
        self.endInsertRows()
        return True

    def removeRows(self, row: int, count: int, parent: QModelIndex = None) -> bool:
        # No parent specified, remove from root
        if parent is None or not parent.isValid():
            parent = self.rootItem

        self.beginRemoveRows(parent, row, row + count - 1)
        parentItem: ClusterTreeItem = parent.internalPointer()
        parentItem.removeChildren(row, count)
        self.endRemoveRows()
        return True

    def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex, destinationChild: int) -> bool:
        # When moving within the same parent, moveRows() is weird:
        # it expects destinationChild to be expectedNewIndex+count when moving downwards
        # it expects destinationChild to be expectedNewIndex when moving upwards

        # Note that if sourceParent and destinationParent are the same, you must ensure that the destinationChild is not
        # within the range of sourceFirst and sourceLast + 1. You must also ensure that you do not attempt to move a row
        # to one of its own children or ancestors. This method returns false if either condition is true, in which case
        # you should abort your move operation.
        if not self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, destinationParent, destinationChild):
            return False

        # When moving downwards within same parent, modify destination child
        if destinationParent is sourceParent and destinationChild > sourceRow:
            destinationChild -= count

        sourceParentItem: ClusterTreeItem = sourceParent.internalPointer()
        destinationParentItem: ClusterTreeItem = destinationParent.internalPointer()

        items = sourceParentItem.popChildren(sourceRow, count)
        destinationParentItem.insertChildren(destinationChild, items)

        self.endMoveRows()
        return True

    # Drag and drop
    def supportedDragActions(self):
        return Qt.DropAction.MoveAction

    def supportedDropActions(self):
        return Qt.DropAction.MoveAction

    def mimeTypes(self):
        return [self._mimeType]

    def mimeData(self, indexes: typing.Iterable[QModelIndex]) -> QMimeData:
        mimeData = QMimeData()
        encodedData = QByteArray()
        stream = QDataStream(encodedData, QIODevice.OpenModeFlag.WriteOnly)

        # Get path to index
        for index in indexes:
            path = []
            parentIndex = index
            while parentIndex.isValid():
                path.insert(0, parentIndex.row())
                parentIndex = parentIndex.parent()


        # rows = [index.row() for index in indexes if index.isValid()]
        # rows.sort()  # Sort row indices in ascending order


    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) -> bool:
        if not data.hasFormat(self._mimeType):
            return False
        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row: int, column: int, parent: QModelIndex) -> bool:
        pass


# noinspection PyPep8Naming
class ClusterSelector(QTreeView):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setModel(ClusterTreeModel(self))
        self.setHeaderHidden(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def load(self, labels, seed=None):
        pass
