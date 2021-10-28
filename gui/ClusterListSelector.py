import typing
import numpy as np
from PyQt6.QtCore import Qt, QModelIndex, QAbstractListModel, QVariant, QMimeData, QByteArray, QDataStream, QIODevice, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush
from PyQt6.QtWidgets import *
import gui


# noinspection PyPep8Naming
class ClusterListSelector(QListView):
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
            # When moving within the same parent, moveRows() is weird:
            # it expects destinationChild to be expectedNewIndex+count when moving downwards
            # it expects destinationChild to be expectedNewIndex when moving upwards
            if not self.beginMoveRows(QModelIndex(), sourceRow, sourceRow + count - 1, QModelIndex(), destinationChild):
                return False

            # Moving up
            if sourceRow > destinationChild:
                movedItems = self.itemData[sourceRow:sourceRow + count]
                del self.itemData[sourceRow:sourceRow + count]
                self.itemData[destinationChild:destinationChild] = movedItems
            # Moving down
            else:
                self.itemData[destinationChild:destinationChild] = self.itemData[sourceRow:sourceRow + count]
                del self.itemData[sourceRow:sourceRow + count]

            self.endMoveRows()
            return True

        # To make items checkable, override flags method and and add Qt.ItemIsUserCheckable
        def flags(self, index: QModelIndex):
            base_flags = QAbstractListModel.flags(self, index)
            if not index.isValid():
                return base_flags | Qt.ItemFlag.ItemIsDropEnabled
            else:
                return base_flags | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled

        # Modify setData: when checking/unchecking an item, it is added/removed from a set.
        def setData(self, index: QModelIndex, value, role=Qt.ItemDataRole.DisplayRole) -> bool:
            if not index.isValid():
                return False

            if role == Qt.ItemDataRole.EditRole or role == Qt.ItemDataRole.DisplayRole:
                oldValue = self.itemData[index.row()].name
                self.itemData[index.row()].name = value
                if oldValue != value:
                    self.dataChanged.emit(index, index, [role])
                return True
            elif role == Qt.ItemDataRole.CheckStateRole:
                oldValue = self.itemData[index.row()].checked
                value = value == Qt.CheckState.Checked
                self.setCheckState(index, value)
                if oldValue != value:
                    self.dataChanged.emit(index, index, [role])
                return True
            else:
                return False

        # Modify data to return checked/unchecked state
        def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
            if not index.isValid():
                return QVariant()
            if role == Qt.ItemDataRole.DisplayRole:
                return f"{index.row() + 1} - {self.itemData[index.row()].name}"
            elif role == Qt.ItemDataRole.CheckStateRole:
                if self.getCheckState(index):
                    return Qt.CheckState.Checked
                else:
                    return Qt.CheckState.Unchecked
            elif role == Qt.ItemDataRole.FontRole:
                return self.itemStyles[index.row()].font
            elif role == Qt.ItemDataRole.BackgroundRole:
                return self.itemStyles[index.row()].bg
            elif role == Qt.ItemDataRole.ForegroundRole:
                return self.itemStyles[index.row()].fg
            else:
                return QVariant()

        def supportedDragActions(self):
            return Qt.DropAction.MoveAction

        def supportedDropActions(self):
            return Qt.DropAction.MoveAction

        def mimeTypes(self):
            return [self._mimeType]

        def mimeData(self, indexes):
            mime_data = QMimeData()
            encoded_data = QByteArray()
            stream = QDataStream(encoded_data, QIODevice.OpenModeFlag.WriteOnly)

            rows = [index.row() for index in indexes if index.isValid()]
            rows.sort() # Sort row indices in ascending order

            for i in rows:
                stream.writeInt(i)

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
            if action == Qt.DropAction.IgnoreAction:
                return True

            # Decode data to determine source index:
            encoded_data = data.data(self._mimeType)
            stream = QDataStream(encoded_data, QIODevice.ReadOnly)
            sourceRow = stream.readInt()
            count = 1
            while not stream.atEnd():
                nextSourceRow = stream.readInt()
                # Ensure row indices are contiguous and in ascending order
                if nextSourceRow - sourceRow != count:
                    raise ValueError("Row indices from MIME stream are not contiguous and in ascending order.")
                count += 1

            # Insert at specific node
            if row != -1:
                destinationRow = row # - 1 if row > sourceRow else row # Moving down is different from moving up
            # Dropping on another item -> insert before it
            elif parent.isValid():
                destinationRow = parent.row()
            # Dropping at blank space below everything -> insert at bottom
            else:
                destinationRow = self.rowCount()

            self.moveRows(QModelIndex(), sourceRow, count, QModelIndex(), destinationRow)

            return False

        def setName(self, index: typing.Union[int, QModelIndex], value: str) -> bool:
            if type(index) is int:
                index = self.index(index, 0)
            if not index.isValid():
                return False
            self.itemData[index.row()].name = value
            return True

        def getName(self, index: typing.Union[int, QModelIndex]):
            if type(index) is int:
                index = self.index(index, 0)
            if not index.isValid():
                return None
            return self.itemData[index.row()].name

        def setCheckState(self, index: typing.Union[int, QModelIndex], checked=True) -> bool:
            if type(index) is int:
                index = self.index(index, 0)

            if not index.isValid():
                return False

            self.itemData[index.row()].checked = checked
            self.itemStyles[index.row()].setHighlight(checked)
            return True

        def getCheckState(self, index: typing.Union[int, QModelIndex]) -> bool:
            if type(index) is int:
                index = self.index(index, 0)
            if index.isValid():
                return self.itemData[index.row()].checked
            else:
                return False












    itemCheckStateChanged = pyqtSignal(int, bool)
    itemsMoved = pyqtSignal(int, int, int)  # source, count, destination

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        model = self.ClusterSelectorModel(self)
        self.setModel(model)
        self.setDropIndicatorShown(True)
        self.setSelectionRectVisible(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ContiguousSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        # Pass rowsMoved event
        model.rowsMoved.connect(self.onRowsMoved)

    def onRowsMoved(self, parent: QModelIndex, start: int, end: int, destination: QModelIndex, row: int):
        self.itemsMoved.emit(start, end - start + 1, row)

    def dataChanged(self, top: QModelIndex, bottom: QModelIndex, roles: typing.Iterable[int] = (), *args, **kwargs):
        super().dataChanged(top, bottom, roles)

        # Handle check/uncheck
        if Qt.ItemDataRole.CheckStateRole in roles:
            for i in range(top.row(), bottom.row() + 1):
                self.itemCheckStateChanged.emit(i, self.model().isChecked(i))

    def load(self, spikeLabels: np.ndarray, clusterNames: list[str] = None, seed: int = None):
        model = self.model()
        model.reset()

        # Empty cluster labels -> show nothing
        if spikeLabels is None or (isinstance(spikeLabels, np.ndarray) and spikeLabels.size == 0):
            return

        # Add data
        nClusters = spikeLabels.max(initial=-1) + 1
        model.insertRows(0, nClusters)
        if clusterNames is None:
            clusterNames = self.randomNames(seed=seed, count=nClusters)
        for i in range(nClusters):
            model.setName(i, clusterNames[i])

    def getItemCheckState(self, i: int):
        return self.model().isChecked(i)

    def getItemName(self, i: int):
        model = self.model()
        return model.getName(i)
        # return model.data(model.index(i, 0), Qt.DisplayRole).name

    def count(self):
        return self.model().rowCount()

    @staticmethod
    def randomNames(seed: int = None, count: int = 1):
        names = (
            "Aardvark",
            "Alligator",
            "Alpaca",
            "Anaconda",
            "Antelope",
            "Ape",
            "Armadillo",
            "Baboon",
            "Badger",
            "Barracuda",
            "Bear",
            "Beaver",
            "Bird",
            "Bison",
            "BlueJay",
            "Bobcat",
            "Buffalo",
            "Butterfly",
            "Buzzard",
            "Camel",
            "Caribou",
            "Carp",
            "Cat",
            "Caterpillar",
            "Catfish",
            "Cheetah",
            "Chicken",
            "Chimpanzee",
            "Chipmunk",
            "Cobra",
            "Cod",
            "Condor",
            "Cougar",
            "Cow",
            "Coyote",
            "Crab",
            "Crane",
            "Cricket",
            "Crocodile",
            "Crow",
            "Deer",
            "Dinosaur",
            "Dog",
            "Dolphin",
            "Donkey",
            "Dove",
            "Dragonfly",
            "Duck",
            "Eagle",
            "Eel",
            "Elephant",
            "Emu",
            "Falcon",
            "Ferret",
            "Finch",
            "Flamingo",
            "Fox",
            "Frog",
            "Goat",
            "Goose",
            "Gopher",
            "Gorilla",
            "Grasshopper",
            "Hamster",
            "Hare",
            "Hawk",
            "Hippopotamus",
            "Horse",
            "Hummingbird",
            "Husky",
            "Iguana",
            "Impala",
            "Kangaroo",
            "Ladybug",
            "Leopard",
            "Lion",
            "Lizard",
            "Llama",
            "Lobster",
            "Mongoose",
            "Monkey",
            "Moose",
            "Mule",
            "Octopus",
            "Orca",
            "Ostrich",
            "Otter",
            "Owl",
            "Ox",
            "Oyster",
            "Panda",
            "Panther",
            "Parrot",
            "Peacock",
            "Pelican",
            "Penguin",
            "Perch",
            "Pheasant",
            "Pig",
            "Pigeon",
            "Porcupine",
            "Quail",
            "Rabbit",
            "Raccoon",
            "Rattlesnake",
            "Raven",
            "Rooster",
            "SeaLion",
            "Sheep",
            "Skunk",
            "Snail",
            "Snake",
            "Tiger",
            "Walrus",
            "Whale",
            "Wolf",
            "Zebra",
        )
        import random
        random.seed(seed)
        return random.sample(names, count)

