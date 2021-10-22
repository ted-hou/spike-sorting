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
        self._checkState = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    def appendChild(self, item: ClusterTreeItem):
        self._children.append(item)
        item.parent = self

    def childAt(self, row: int) -> ClusterTreeItem | None:
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

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.rootItem = ClusterTreeItem('Root')
        a = ClusterTreeItem('A')
        b = ClusterTreeItem('A')
        c = ClusterTreeItem('A')
        self.rootItem.appendChild(a)
        self.rootItem.appendChild(b)
        self.rootItem.appendChild(c)
        a.appendChild(ClusterTreeItem('A1'))
        a.appendChild(ClusterTreeItem('A2'))

    def __del__(self):
        del self.rootItem

    def index(self, row: int, column: int, parent: QModelIndex = None) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if parent is not None and parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self.rootItem

        childItem = parentItem.childAt(row)
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

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        baseFlags = QAbstractItemModel.flags(self, index)
        if not index.isValid():
            return baseFlags | Qt.ItemFlag.ItemIsDropEnabled
        else:
            return baseFlags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = ...):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.rootItem.name
        return QVariant()


# noinspection PyPep8Naming
class ClusterSelector(QTreeView):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setModel(ClusterTreeModel(self))
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDropIndicatorShown(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    def load(self, *args, **kwargs):
        pass
