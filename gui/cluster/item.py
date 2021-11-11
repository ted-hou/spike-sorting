from __future__ import annotations  # allows TreeItem type hint in its own constructor
import typing
from abc import ABC, abstractmethod
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from ..color import ColorRange


# noinspection PyPep8Naming
class ClusterItem(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def indices(self) -> np.ndarray:
        ...

    @property
    @abstractmethod
    def color(self) -> QColor:
        ...

    @property
    @abstractmethod
    def visible(self) -> bool:
        ...

    def isLeaf(self) -> bool:
        return True

    def isBranch(self) -> bool:
        return False

    def __eq__(self, other):
        return self.name == other.name
        # return np.array_equal(self.indices, other.indices)

    def __hash__(self):
        return hash(self.name)
        # return hash(self.indices.tobytes())

    def __ne__(self, other):
        return not(self == other)


# noinspection PyPep8Naming
class ClusterTreeItem(ClusterItem):
    """
    Tree item containing a parent TreeItem reference, a list of children TreeItems, and its own data as a QVariant
    """

    _children: list[ClusterTreeItem]
    _parent: ClusterTreeItem | None
    _name: str = ''
    _checkState: Qt.CheckState = Qt.CheckState.Checked
    _indices: np.ndarray | None
    _cachedIndices: np.ndarray | None
    _dirty: bool
    _colorRange: ColorRange

    def __init__(self, name: str, indices: np.ndarray = None, checkState: Qt.CheckState = Qt.CheckState.Checked, colorRange: ColorRange = None):
        super().__init__()
        self._name = name
        self._checkState = checkState
        self._children = []
        self._parent = None
        self._indices = indices
        self._cachedIndices = None
        self._dirty = True
        self._colorRange = ColorRange() if colorRange is None else colorRange

    @staticmethod
    def fromIndices(name: str, indices: list) -> ClusterTreeItem:
        if len(indices) == 1 and isinstance(indices[0], list):
            return ClusterTreeItem(name, indices[0])

        item = ClusterTreeItem(name)

        for i in range(len(indices)):
            if isinstance(indices[i], np.ndarray):
                childItem = ClusterTreeItem(f"{name}-{i + 1}", indices[i])
            else:
                childItem = ClusterTreeItem.fromIndices(f"{name}-{i + 1}", indices[i])
            item.insertChild(item.childCount(), childItem)
        return item

    def isValid(self) -> bool:
        """Either a branch node, or a leaf node with non-empty indices."""
        return self.childCount() > 0 or self._indices is not None

    def isLeaf(self):
        """A leaf node has no children."""
        return not self.isBranch()

    def isBranch(self):
        """A branch node has one or more children, but does not contain indices data directly."""
        return self.childCount() > 0

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
                size = self.size
                self._cachedIndices = np.empty((size,), dtype=np.uint32)
                i = 0
                for child in self._children:
                    childIndices = child.indices
                    self._cachedIndices[i:i + childIndices.size] = childIndices
                    i += childIndices.size
                self.dirty = False
            return self._cachedIndices

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

    @property
    def size(self) -> int:
        if self.childCount() == 0:
            return self._indices.size if self._indices is not None else 0
        else:
            count = 0
            for child in self._children:
                count += child.size
            return count

    @property
    def visible(self) -> bool:
        return self.checkState == Qt.CheckState.Checked

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

    @property
    def color(self):
        if self.childCount() == 0:
            return self.colorRange.color
        else:
            return QColor(0, 0, 0)

    @property
    def colorRange(self):
        return self._colorRange

    @colorRange.setter
    def colorRange(self, value: ColorRange):
        self._colorRange = value

    def children(self):
        """Return a list of child items. This list is a copy of the internal list so it's safe to modify."""
        return self._children.copy()

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

    def removeChildren(self, row: int, count: int) -> typing.Sequence[ClusterTreeItem]:
        for c in self._children[row:row + count]:
            c.parent = None
        items = self._children[row:row + count]
        del self._children[row:row + count]
        self.indices = None
        self.dirty = True
        return items

    def insertChild(self, row: int, item: ClusterTreeItem):
        self.insertChildren(row, [item])

    def removeChild(self, row: int) -> ClusterTreeItem:
        return self.removeChildren(row, 1)[0]

    def copy(self) -> ClusterTreeItem:
        """Return a childless shallow copy of the item"""
        obj = ClusterTreeItem(name=self._name, indices=self._indices, checkState=self._checkState, colorRange=self.colorRange)
        return obj

    def leaves(self) -> list[ClusterTreeItem]:
        """Return all leaf nodes in the tree."""
        if self.isLeaf():
            return [self]
        else:
            items = []
            for child in self._children:
                if child.childCount() == 0 and child._indices is not None:
                    items.append(child)
                elif child.childCount() > 0:
                    items.extend(child.leaves())
            return items

    def branches(self) -> list[ClusterTreeItem]:
        """Return all branch nodes in the tree."""
        items = []
        if self.isBranch():
            items.append(self)
            for child in self._children:
                items.extend(child.branches())
        return items

    def traversal(self) -> list[ClusterTreeItem]:
        """Returns all items from a pre-order traversal of the tree."""
        items = [self]
        if len(self._children) > 0:
            for child in self._children:
                items.extend(child.traversal())
        return items

    @staticmethod
    def containsDirectDescendants(items: typing.Iterable[ClusterTreeItem]):
        """Check if any item in the list is a direct descendant of another item in the list."""
        # We'll do this by checking if an item's parent, or grandparent, or great grandparent... are also in the list.
        for item in items:
            parent = item.parent
            while parent is not None:
                if parent in items:
                    return True
                parent = parent.parent
        return False

    @staticmethod
    def merge(items: list[ClusterTreeItem], name: str):
        # ensure items in list are direct descendents/ancestors of one another
        if ClusterTreeItem.containsDirectDescendants(items):
            raise ValueError(f"Cannot merge all {len(items)} items because list contains direct descendants.")

        # Convert branch nodes to leaf nodes
        leafItems = items.copy()
        for item in leafItems:
            if item.isBranch():
                leafItems.remove(item)
                leafItems.extend(item.leaves())

        # Pre-allocate and merge indices
        size = 0
        for item in leafItems:
            size += item.size
        mergedIndices = np.empty((size,), dtype=np.uint32)
        i = 0
        for item in leafItems:
            mergedIndices[i:i+item.size] = item.indices
            i += item.size

        # Find the widest ColorRange among all items
        maxColorRange = max(items, key=lambda it: it.colorRange.width).colorRange

        mergedItem = ClusterTreeItem(name=name, indices=mergedIndices, checkState=Qt.CheckState.Checked, colorRange=maxColorRange)
        return mergedItem

    def split(self, data, method='kmeans', n=3) -> ClusterTreeItem:
        """
        Split an item into n subclusters.
        :param data: spike features (see spikesorting.cluster). Can be np.ndarray or SpikeFeatures
        :param method: clustering method, default 'kmeans'
        :param n: number of clusters
        :return: ClusterTreeItem containing all sub-clusters as child items
        """
        from spikeclustering import cluster
        labels = cluster(data.features[self.indices, :], n_clusters=n, method=method)
        nSubClusters = labels.max(initial=-1) + 1

        indices = self.indices
        splitIndices = []
        for i in range(nSubClusters):
            splitIndices.append(indices[labels == i])

        item = ClusterTreeItem.fromIndices(f"{self.name}", splitIndices)
        item._colorRange = self._colorRange
        item._checkState = Qt.CheckState.Checked
        return item