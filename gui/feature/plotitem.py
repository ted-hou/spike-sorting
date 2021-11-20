import typing
import numpy as np
import pyqtgraph as pg
from pyqtgraph import GraphicsObject
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QColor, QBrush, QPen
from gui.cluster import ClusterItem
from abc import ABC, abstractmethod


# noinspection PyPep8Naming
class FeaturePlotItem(pg.ScatterPlotItem):
    cluster: ClusterItem
    _globalSelectionMask: np.ndarray
    _localSelectionMask: np.ndarray
    features: np.ndarray  # (n_spikes, n_dims)
    pen: np.ndarray
    brush: np.ndarray
    _dims: tuple[int, int]

    def __init__(self, features: np.ndarray, cluster: ClusterItem = None, selectionMask: np.ndarray = None, dims: typing.Union[str, tuple[int, int]] = (0, 1)):
        self.cluster = cluster
        self._globalSelectionMask = selectionMask
        self._localSelectionMask = selectionMask[cluster.indices] if selectionMask is not None else None
        self.features = features
        self.dims = dims
        pg.ScatterPlotItem.__init__(self, pos=features[cluster.indices, :][:, self.dims], size=2)
        self.pen = None
        self.brush = None
        self.setSelectionMask(selectionMask)

    @property
    def globalSelectionMask(self):
        """np.ndarray of booleans. (n_spikes_total, )"""
        return self._globalSelectionMask

    @property
    def localSelectionMask(self):
        """np.ndarray of booleans. (n_spikes_in_cluster, )"""
        return self._localSelectionMask

    @property
    def dims(self) -> tuple[int, int]:
        return self._dims

    @dims.setter
    def dims(self, value: typing.Union[str, tuple[int, int]]):
        if isinstance(value, str):
            if value == 'xy':
                self._dims = (0, 1)
            elif value == 'xz':
                self._dims = (0, 2)
            elif value == 'yz':
                self._dims = (1, 2)
            else:
                raise ValueError(f"Unsupported dims value: {value}")
        else:
            self._dims = value

    def setSelectionMask(self, selectionMask: np.ndarray):
        """
        :param selectionMask: np.ndarray of booleans. (n_spikes_total, )
        :return:
        """
        self._globalSelectionMask = selectionMask
        self._localSelectionMask = selectionMask[self.cluster.indices] if selectionMask is not None else None
        self.onSelectionMaskChanged(self._globalSelectionMask, self._localSelectionMask)

    def onSelectionMaskChanged(self, globalMask: np.ndarray, localMask: np.ndarray):
        self.pen = self.createPens()
        self.brush = self.createBrushes()
        self.setPen(self.pen)
        self.setBrush(self.brush)

    def createPens(self) -> np.ndarray:
        return self._createStyles(QPen, pg.mkPen, self.pen)

    def createBrushes(self) -> np.ndarray:
        return self._createStyles(QBrush, pg.mkBrush, self.brush)

    def _createStyles(self, dtype, method, array: np.ndarray = None):
        if self.localSelectionMask is None:
            return method(self.cluster.color)

        # Create array, or validate array size
        size = self.cluster.size
        if array is None:
            array = np.empty((size,), dtype=dtype)
        elif array.shape != (size, ):
            raise ValueError(f"Provided array has shape {array.shape}, does not match required shape {(size,)}")

        array[self.localSelectionMask] = method(self.cluster.color)
        array[np.invert(self.localSelectionMask)] = method(QColor('black'))

        return array
