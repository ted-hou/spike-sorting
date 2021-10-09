import typing
import numpy as np
from PyQt5.QtCore import Qt, QModelIndex, QAbstractListModel, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QBrush
from PyQt5.QtWidgets import *
import gui


# noinspection PyPep8Naming
class ClusterSelector(QListView):
    # noinspection PyPep8Naming
    class ClusterSelectorModel(QAbstractListModel):
        class ItemData:
            name: str = ''
            checked: bool = True

            def __init__(self, name):
                self.name = name

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
                    self.bg = color
                    self.fg = QColor('white')
                else:
                    self.bg = QColor('white')
                    self.fg = color
                self.color = color

            def setHighlight(self, highlight=True):
                if highlight:
                    self.font.setBold(True)
                    self.bg = self.color
                    self.fg = QColor('white')
                else:
                    self.font.setBold(False)
                    self.bg = QColor('white')
                    self.fg = self.color

        # Data
        itemData: list[ItemData] = []
        itemStyles: list[ItemStyle] = []
        _mimeType = "application/vnd.text.list"

        def __init__(self, parent=None):
            super().__init__(parent)

        def reset(self):
            self.beginResetModel()
            self.itemData.clear()
            self.itemStyles.clear()
            self.endResetModel()

        def rowCount(self, parent=None) -> int:
            return len(self.itemData)

        def insertRows(self, row, count, parent=QModelIndex()) -> bool:
            if parent is not None and parent.isValid():
                return False

            self.beginInsertRows(parent, row, row + count - 1)
            for i in range(count):
                self.itemData.insert(row + i, self.ItemData(str(i)))
            if len(self.itemData) > len(self.itemStyles):
                self.itemStyles = [self.ItemStyle(gui.default_color(i), self.itemData[i].checked) for i in
                                   range(len(self.itemData))]
            self.endInsertRows()
            return True

        def removeRows(self, row, count, parent=None) -> bool:
            if parent is not None and parent.isValid():
                return False
            self.beginRemoveRows(parent, row, row + count - 1)
            del self.itemData[row:row + count]
            self.endRemoveRows()
            self.itemStyles = [self.ItemStyle(gui.default_color(i), self.itemData[i].checked) for i in
                               range(len(self.itemData))]
            return True

        def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex, destinationChild: int) -> bool:
            if count > 1:
                raise ValueError(f"Error attempting to move {count} items. Only moving one item at a time is supported.")

            print(f"Moveing rows ({sourceRow} - {sourceRow + count - 1}) to {destinationChild}")
            # When moving within the same parent, beginMoveRows() is weird:
            # it expects destinationChild to be expectedNewIndex+1 when moving downwards
            # it expects destinationChild to be expectedNewIndex when moving upwards
            if not self.beginMoveRows(QModelIndex(), sourceRow, sourceRow + count - 1, QModelIndex(), destinationChild + 1 if sourceRow < destinationChild else destinationChild):
                return False

            # sourceRow = sourceRow + count - 1 if destinationChild < sourceRow else sourceRow
            for i in range(count):
                self.itemData.insert(destinationChild, self.itemData.pop(sourceRow))
            self.endMoveRows()
            return True

        # To make items checkable, override flags method and and add Qt.ItemIsUserCheckable
        def flags(self, index: QModelIndex):
            base_flags = QAbstractListModel.flags(self, index)
            if not index.isValid():
                return base_flags | Qt.ItemIsDropEnabled
            else:
                return base_flags | Qt.ItemIsUserCheckable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

        # Modify setData: when checking/unchecking an item, it is added/removed from a set.
        def setData(self, index: QModelIndex, value, role=Qt.DisplayRole) -> bool:
            if not index.isValid():
                return False

            if role == Qt.EditRole or role == Qt.DisplayRole:
                oldValue = self.itemData[index.row()].name
                self.itemData[index.row()].name = value
                if oldValue != value:
                    self.dataChanged.emit(index, index, [role])
                return True
            elif role == Qt.CheckStateRole:
                oldValue = self.itemData[index.row()].checked
                value = value == Qt.Checked
                self.setChecked(index, value)
                if oldValue != value:
                    self.dataChanged.emit(index, index, [role])
                return True
            else:
                return False

        # Modify data to return checked/unchecked state
        def data(self, index: QModelIndex, role=Qt.DisplayRole):
            if not index.isValid():
                return QVariant()
            if role == Qt.DisplayRole:
                return self.itemData[index.row()].name
            elif role == Qt.CheckStateRole:
                if self.isChecked(index):
                    return Qt.Checked
                else:
                    return Qt.Unchecked
            elif role == Qt.FontRole:
                return self.itemStyles[index.row()].font
            elif role == Qt.BackgroundRole:
                return self.itemStyles[index.row()].bg
            elif role == Qt.ForegroundRole:
                return self.itemStyles[index.row()].fg
            else:
                return QVariant()

        def supportedDragActions(self):
            return Qt.MoveAction

        def supportedDropActions(self):
            return Qt.MoveAction

        def mimeTypes(self):
            return [self._mimeType]

        def mimeData(self, indexes):
            mime_data = QMimeData()
            encoded_data = QByteArray()
            stream = QDataStream(encoded_data, QIODevice.WriteOnly)

            for index in indexes:
                if index.isValid():
                    # name = self.data(index, Qt.DisplayRole)
                    # checked = self.data(index, Qt.CheckStateRole)
                    stream.writeInt(index.row())
                    # stream.writeQString(name)
                    # stream.writeInt8(checked)

            mime_data.setData(self._mimeType, encoded_data)
            return mime_data

        def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row, column, parent: QModelIndex) -> bool:
            if not data.hasFormat(self._mimeType):
                return False
            return True

        def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row, column, parent: QModelIndex) -> bool:
            """Handles Drag&Drop by inserting dropped items via insertRows(). removeRows() is then automatically
            called by QAbstractItemView """
            if not self.canDropMimeData(data, action, row, column, parent):
                return False
            if action == Qt.IgnoreAction:
                return True

            # Decode data to determine source index:
            encoded_data = data.data(self._mimeType)
            stream = QDataStream(encoded_data, QIODevice.ReadOnly)
            while not stream.atEnd():
                sourceRow = stream.readInt()
                # self.moveRows(QModelIndex(), srcRow, 1, QModelIndex(), tgtRow)
            if not stream.atEnd():
                raise ValueError("MIME stream contains more than one entry. Only single-item drag and drops are supported.")

            # Insert at specific node
            if row != -1:
                destinationRow = row
            # Dropping on another item -> insert before it
            elif parent.isValid():
                destinationRow = parent.row()
            # Dropping at blank space below everything -> insert at bottom
            else:
                destinationRow = self.rowCount() - 1

            self.moveRows(QModelIndex(), sourceRow, 1, QModelIndex(), destinationRow)

            return False

        def setChecked(self, index: typing.Union[int, QModelIndex], checked=True) -> bool:
            if type(index) is int:
                index = self.index(index, index)

            if not index.isValid():
                return False

            self.itemData[index.row()].checked = checked
            self.itemStyles[index.row()].setHighlight(checked)
            return True

        def isChecked(self, index: typing.Union[int, QModelIndex]) -> bool:
            if type(index) is int:
                index = self.index(index, 0)
            if index.isValid():
                return self.itemData[index.row()].checked
            else:
                return False

    itemCheckStateChanged = pyqtSignal(int, bool)
    itemMoved = pyqtSignal(int, int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        model = self.ClusterSelectorModel(self)
        self.setModel(model)
        self.setDropIndicatorShown(True)
        self.setSelectionRectVisible(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

    def dataChanged(self, top: QModelIndex, bottom: QModelIndex, roles: typing.Iterable[int] = (), *args, **kwargs):
        super().dataChanged(top, bottom, roles)

        # Handle check/uncheck
        if Qt.CheckStateRole in roles:
            for i in range(top.row(), bottom.row() + 1):
                self.itemCheckStateChanged.emit(i, self.model().isChecked(i))

    def load(self, spikeLabels: np.ndarray):
        model = self.model()
        model.reset()

        # Empty labels -> show nothing
        if spikeLabels is None or (isinstance(spikeLabels, np.ndarray) and spikeLabels.size == 0):
            return

        # Add data
        model.insertRows(0, spikeLabels.max() + 1)
