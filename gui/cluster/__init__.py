from .item import *
from .model import *
from .view import *

__all__ = ["ClusterItem", "ClusterTreeItem", "ClusterTreeModel", "ClusterSelector"]


# noinspection PyPep8Naming
def labelsToIndices(labels: np.ndarray) -> list[np.ndarray]:
    indices = []
    for i in np.unique(labels):
        indices.append(np.where(labels == i)[0])
    return indices


# noinspection PyPep8Naming
def indicesToLabels(indices: list[np.ndarray], out_labels: np.ndarray = None) -> np.ndarray:
    size = sum([np.size(i) for i in indices])
    if out_labels is None:
        out_labels = np.empty((size,), np.uint32)
    elif out_labels.shape != (size,):
        raise ValueError(f"out_labels {out_labels.shape} does not have desired shape ({size},)")

    for i in range(len(indices)):
        out_labels[indices[i]] = i

    return out_labels
