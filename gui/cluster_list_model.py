import typing
from PyQt5.QtCore import Qt, QModelIndex, QAbstractListModel, QVariant, QMimeData, QByteArray, \
    QDataStream, QIODevice
from PyQt5.QtGui import QColor, QFont, QBrush
import gui


class ClusterListModel(QAbstractListModel):
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

    itemData: list[ItemData]
    itemStyles: list[ItemStyle]
    _mimeType = "application/vnd.text.list"

    def __init__(self, parent=None):
        super(ClusterListModel, self).__init__(parent)
        self.itemData = [self.ItemData(str(i)) for i in range(5)]
        self.itemStyles = [self.ItemStyle(gui.default_color(i), True) for i in range(5)]

    def rowCount(self, parent=None) -> int:
        return len(self.itemData)

    def insertRows(self, row, count, parent=None) -> bool:
        if parent is not None and parent.isValid():
            return False

        self.beginInsertRows(parent, row, row + count - 1)
        for i in range(count):
            self.itemData.insert(row + i, ClusterListModel.ItemData(str(i)))
        if len(self.itemData) > len(self.itemStyles):
            self.itemStyles = [self.ItemStyle(gui.default_color(i), self.itemData[i].checked) for i in range(len(self.itemData))]
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=None) -> bool:
        if parent is not None and parent.isValid():
            return False
        self.beginRemoveRows(parent, row, row + count - 1)
        del self.itemData[row:row+count]
        self.endRemoveRows()
        self.itemStyles = [self.ItemStyle(gui.default_color(i), self.itemData[i].checked) for i in
                           range(len(self.itemData))]
        return True

    def moveRows(self, sourceParent: QModelIndex, sourceRow: int, count: int, destinationParent: QModelIndex, destinationChild: int) -> bool:
        if sourceRow < 0 or sourceRow + count - 1 >= self.rowCount(sourceParent) or destinationChild <= 0 or destinationChild > self.rowCount(destinationParent) or sourceRow == destinationChild - 1 or count <= 0:
            return False

        if not self.beginMoveRows(QModelIndex(), sourceRow, sourceRow + count - 1, QModelIndex(), destinationChild):
            return False

        destinationChild -= 1
        from_row = sourceRow + count - 1 if destinationChild < sourceRow else sourceRow
        for i in range(count):
            self.itemData.insert(destinationChild, self.itemData.pop(from_row))
        self.endMoveRows()
        return True


    # To make items checkable, override flags method and and add Qt.ItemIsUserCheckable
    def flags(self, index: QModelIndex):
        base_flags = QAbstractListModel.flags(self, index)
        if not index.isValid():
            return base_flags | Qt.ItemIsDropEnabled
        else:
            return base_flags | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled

        # base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        # if index.isValid():
        #     return base_flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsEditable
        # else:
        #     return base_flags | Qt.ItemIsDropEnabled

    # Modify setData: when checking/unchecking an item, it is added/removed from a set.
    def setData(self, index: QModelIndex, value, role=Qt.DisplayRole) -> bool:
        if not index.isValid():
            return False

        if role == Qt.EditRole or role == Qt.DisplayRole:
            self.itemData[index.row()].name = value
            self.dataChanged.emit(index, index)
            return True
        elif role == Qt.CheckStateRole:
            self.setChecked(index, value == Qt.Checked)
            self.dataChanged.emit(index, index)
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
            if self.getChecked(index):
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
        return QAbstractListModel.supportedDragActions(self) | Qt.MoveAction

    def mimeTypes(self):
        return [self._mimeType]

    def mimeData(self, indexes):
        mime_data = QMimeData()
        encoded_data = QByteArray()
        stream = QDataStream(encoded_data, QIODevice.WriteOnly)

        for index in indexes:
            if index.isValid():
                name = self.data(index, Qt.DisplayRole)
                checked = self.data(index, Qt.CheckStateRole)
                stream.writeQString(name)
                stream.writeInt8(checked)

        mime_data.setData(self._mimeType, encoded_data)
        return mime_data

    def canDropMimeData(self, data: QMimeData, action: Qt.DropAction, row, column, parent: QModelIndex) -> bool:
        if not data.hasFormat(self._mimeType):
            return False
        return True

    def dropMimeData(self, data: QMimeData, action: Qt.DropAction, row, column, parent: QModelIndex) -> bool:
        if not self.canDropMimeData(data, action, row, column, parent):
            return False
        if action == Qt.IgnoreAction:
            return True

        # Insert between/above/below existing node
        if row != -1:
            begin_row = row
        # Insert before a parent item's children
        elif parent.isValid():
            begin_row = parent.row()
        # Invalid parent, invalid row index, insert at bottom
        else:
            begin_row = self.rowCount()

        encoded_data = data.data(self._mimeType)
        stream = QDataStream(encoded_data, QIODevice.ReadOnly)
        new_items = []
        rows = 0

        while not stream.atEnd():
            name = stream.readQString()
            checked = stream.readInt8()
            new_items.append((name, checked))
            rows += 1

        self.insertRows(begin_row, rows, QModelIndex())
        for data in new_items:
            index = self.index(begin_row, 0)
            self.setData(index, data[0], Qt.DisplayRole)
            self.setData(index, data[1], Qt.CheckStateRole)
            begin_row += 1

        return True

    def getChecked(self, index: typing.Union[int, QModelIndex]) -> bool:
        if type(index) is int:
            index = self.index(index, index)
        if index.isValid():
            return self.itemData[index.row()].checked
        else:
            return False

    def setChecked(self, index: typing.Union[int, QModelIndex], checked=True) -> bool:
        if type(index) is int:
            index = self.index(index, index)

        if not index.isValid():
            return False

        self.itemData[index.row()].checked = checked
        self.itemStyles[index.row()].setHighlight(checked)
        return True
