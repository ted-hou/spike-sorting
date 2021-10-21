import typing
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from spikedata import SpikeData

COMBOBOX_WIDTH = 38
BUTTON_WIDTH = 25
ITEM_HEIGHT = 20
SPACING = 1
MARGIN = 5
WIDTH_THRESHOLD_1 = 230
WIDTH_THRESHOLD_2 = 185
MIN_WIDTH = 160
MIN_HEIGHT = 30


# noinspection PyPep8Naming
class ChannelSelector(QWidget):
    prevButton: QPushButton
    nextButton: QPushButton
    channelComboBox: QComboBox
    electrodeComboBox: QComboBox
    channelLabel: QLabel
    electrodeLabel: QLabel

    channels: list[int]
    electrodes: list[int]
    currentIndex = -1
    currentChannel = -1
    currentElectrode = -1
    _sizeHint = QSize(WIDTH_THRESHOLD_2, MIN_HEIGHT + 10)
    _minSizeHint = QSize(MIN_WIDTH, MIN_HEIGHT)

    # Signals
    currentIndexChanged = pyqtSignal(int)

    def __init__(self, parent=None, flags=None):
        super().__init__(parent, flags)
        self.createWidgets()
        self.setSizeLimits(comboBoxWidth=COMBOBOX_WIDTH, buttonWidth=BUTTON_WIDTH, itemHeight=ITEM_HEIGHT, spacing=SPACING, margin=MARGIN)
        self.createConnections()

    def load(self, spikeData: typing.Union[SpikeData, list[SpikeData]]):
        self.channelComboBox.clear()
        self.electrodeComboBox.clear()

        # load(None) clears all data
        if spikeData is None:
            self.channels = []
            self.electrodes = []
            return

        # load list of SpikeData
        if type(spikeData) is list:
            self.channels = [sd.channel for sd in spikeData]
            self.electrodes = [sd.electrode for sd in spikeData]
        elif isinstance(spikeData, SpikeData):
            self.channels = [spikeData.channel]
            self.electrodes = [spikeData.electrode]
        else:
            raise TypeError(f"spikeData is {type(spikeData)}, expected list[SpikeData], or SpikeData.")

        self.channelComboBox.insertItems(0, [str(i) for i in self.channels])
        self.electrodeComboBox.insertItems(0, [str(i) for i in self.electrodes])
        self.setCurrentIndex(0)

    def setSizeLimits(self, comboBoxWidth, buttonWidth, itemHeight, spacing=2, margin=11):
        buttonSize = (buttonWidth, itemHeight)
        comboBoxSize = (comboBoxWidth, itemHeight)

        self.channelComboBox.setMinimumSize(*comboBoxSize)
        self.electrodeComboBox.setMinimumSize(*comboBoxSize)
        self.prevButton.setMaximumSize(*buttonSize)
        self.nextButton.setMaximumSize(*buttonSize)

        layout = self.layout()
        layout.setSpacing(spacing)
        layout.setContentsMargins(margin, margin, margin, margin)

    def resizeEvent(self, event: QResizeEvent):
        super(ChannelSelector, self).resizeEvent(event)

        # Abbreviate label text based on layout width
        if event.oldSize().width() < WIDTH_THRESHOLD_1 <= event.size().width():
            self.channelLabel.setText("channel:")
            self.electrodeLabel.setText("electrode:")
        elif event.oldSize().width() >= WIDTH_THRESHOLD_1 > event.size().width() or event.oldSize().width() < WIDTH_THRESHOLD_2 <= event.size().width():
            self.channelLabel.setText("chn:")
            self.electrodeLabel.setText("elec:")
        elif event.oldSize().width() >= WIDTH_THRESHOLD_2 > event.size().width():
            self.channelLabel.setText("c:")
            self.electrodeLabel.setText("e:")

    def sizeHint(self):
        return self._sizeHint

    def minimumSizeHint(self):
        return self._minSizeHint

    def createWidgets(self):
        layout = QHBoxLayout(self)
        leftButton = QPushButton("<")
        rightButton = QPushButton(">")
        channelLabel = QLabel("chn:")
        channelComboBox = QComboBox()
        # channelComboBox.insertItems(0, [str(i) for i in self.channels])

        electrodeLabel = QLabel("elec:")
        electrodeComboBox = QComboBox()
        # electrodeComboBox.insertItems(0, [str(i) for i in self.electrodes])

        layout.addStretch(1)
        layout.addWidget(leftButton, 1)
        layout.addWidget(channelLabel, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(channelComboBox, 2)
        layout.addWidget(electrodeLabel, 2, Qt.AlignmentFlag.AlignRight)
        layout.addWidget(electrodeComboBox, 2)
        layout.addWidget(rightButton, 1)
        layout.addStretch(1)

        self.setLayout(layout)

        self.prevButton = leftButton
        self.nextButton = rightButton
        self.channelComboBox = channelComboBox
        self.electrodeComboBox = electrodeComboBox
        self.channelLabel = channelLabel
        self.electrodeLabel = electrodeLabel

    def createConnections(self):
        self.channelComboBox.activated.connect(self.setCurrentIndex)
        self.electrodeComboBox.activated.connect(self.setCurrentIndex)
        self.prevButton.clicked.connect(self.prev)
        self.nextButton.clicked.connect(self.next)

    def destroyConnections(self):
        self.channelComboBox.activated.disconnect(self.setCurrentIndex)
        self.electrodeComboBox.activated.disconnect(self.setCurrentIndex)
        self.prevButton.clicked.disconnect(self.prev)
        self.nextButton.clicked.disconnect(self.next)

    def next(self):
        i = self.currentIndex + 1
        if i >= len(self.channels):
            i = 0
        self.setCurrentIndex(i)

    def prev(self):
        i = self.currentIndex - 1
        if i < 0:
            i = len(self.channels) - 1
        self.setCurrentIndex(i)

    def setCurrentIndex(self, i: int):
        if i < 0 or i >= len(self.channels):
            raise ValueError(f"Requested index {i} is out of range [0, {len(self.channels)})")

        if self.currentIndex == i:
            return

        self.currentIndex = i
        self.currentChannel = self.channels[i]
        self.currentElectrode = self.electrodes[i]
        self.channelComboBox.setCurrentIndex(i)
        self.electrodeComboBox.setCurrentIndex(i)

        self.currentIndexChanged.emit(self.currentIndex)

    def setCurrentChannel(self, channel: int):
        i = self.channels.index(channel)
        if i < 0:
            raise ValueError(f"Requested channel ({channel}) not available")
        self.setCurrentIndex(i)

    def setCurrentElectrode(self, electrode: int):
        channel = self.electrodes.index(electrode)
        if channel < 0:
            raise ValueError(f"Requested electrode ({electrode}) not found.")
        self.setCurrentChannel(channel)
