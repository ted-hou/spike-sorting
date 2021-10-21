from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
import numpy as np
from PyQt5.QtCore import Qt, QModelIndex, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal, \
    QAbstractItemModel, QObject
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import *
import gui


# noinspection PyPep8Naming
class ItemStyle:
    font: QFont
    fg: typing.Union[QColor, QBrush]
    bg: typing.Union[QColor, QBrush]
    color: QColor
    highlighted: bool = False

    def __init__(self, color: typing.Union[QColor, str], highlight=False):
        self.highlighted = highlight
        self.setColor(color)
        self.font = QFont()
        self.font.setBold(highlight)

    def setColor(self, color: typing.Union[QColor, str]):
        if type(color) is str:
            color = QColor(color)
        if not isinstance(color, QColor):
            raise TypeError(f"color is type {type(color)}, expected QColor or str")
        if self.highlighted:
            self.bg = QColor('white')
            self.fg = color
            # self.bg = color
            # self.fg = QColor('white')
        else:
            self.bg = QColor('white')
            self.fg = color
        self.color = color

    def setHighlight(self, highlight=True):
        if highlight:
            self.font.setBold(True)
            # self.bg = self.color
            # self.fg = QColor('white')
        else:
            self.font.setBold(False)
            # self.bg = QColor('white')
            # self.fg = self.color


# noinspection PyPep8Naming
class ClusterTreeItem:
    """
    Tree item containing a parent TreeItem reference, a list of children TreeItems, and its own data as a QVariant
    """

    _children: list[ClusterTreeItem]
    _parent: ClusterTreeItem
    _name: str = ''
    _checked: bool = True

    def __init__(self, name: str, parent: ClusterTreeItem = None):
        self.parent = parent
        self._name = name
        self._checked = True
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
    def checked(self):
        return self._checked

    @checked.setter
    def checked(self, value: bool):
        self._checked = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    def appendChild(self, item: ClusterTreeItem):
        self._children.append(item)

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
        self.rootItem = ClusterTreeItem('Cluster')

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
        

# noinspection PyPep8Naming
class ClusterTreeSelector(QTreeView):
    pass
