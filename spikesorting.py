import typing
import warnings

import numpy as np
from scipy.cluster.vq import kmeans2
from spikefeatures import SpikeFeatures, SpikeFeaturesPCA, SpikeFeaturesHaar, SpikeFeaturesDb4
from spikedata import SpikeData


def extract_features(data, ndims=5, method='haar'):
    """
    Extract features from spike waveforms.
    :param data: waveforms as an NumPy array with shape (n_waveforms, n_samples_per_waveform), or SpikeData object, or a list of NumPy arrays or SpikeData objects.
    :param ndims: number of features to extract. This should be <= waveform length
    :param method: feature extraction method, can be 'pca', 'haar', 'db4'
    :return: SpikeFeatures object, or a list of SpikeFeature objects, depending on whether 'data' itself is a list
    """

    if type(data) is list:
        return [extract_features(d, ndims=ndims, method=method) for d in data]
    elif isinstance(data, SpikeData):
        data = data.waveforms

    if not isinstance(data, np.ndarray):
        raise TypeError(f"data is type {type(data)}, expected np.ndarray, SpikeData, or list[SpikeData]")

    if method in ('haar', 'dwt'):
        features = SpikeFeaturesHaar(data)
    elif method == 'db4':
        features = SpikeFeaturesDb4(data)
    elif method == 'pca':
        features = SpikeFeaturesPCA(data)
    else:
        raise ValueError(f"Unsupported feature extraction method '{method}', expected 'haar', 'db4', 'pca'")

    features.reduce(ndims)

    return features


def cluster(data, n_clusters=3, method='kmeans'):
    if type(data) is list:
        return [cluster(d) for d in data]

    if isinstance(data, SpikeFeatures):
        data = data.features

    if not isinstance(data, np.ndarray):
        raise TypeError(f"data is type {type(data)}, expected np.ndarray, SpikeFeatures, or list[SpikeFeatures]")

    if method == 'kmeans':
        _, labels = kmeans2(data, n_clusters)
        return labels
    else:
        raise ValueError(f"Unsupported clustering method {method}, expected 'kmeans', 'gaussian', 'nn'")


def move_clusters(labels: np.ndarray, source: int, count: int, destination: int, in_place=False):
    """
    Reorder existing cluster labels by moving one cluster (or several contiguous clusters) to a new index. The new
    cluster labels will still start at 0 and end at n_clusters. By default returns a modified copy unless in_place=True

    :param labels: 1d NumPy array containing cluster labels [0, N)
    :param source: first cluster index to be moved
    :param count: number of clusters to be moved
    :param destination: destination index to move source to, actual index they end up in is: destination (if moving up), destination - count (if moving down)
    :param in_place: (default False) True to modify original labels array. False to return a modified copy. Performance is the same either way
    :return: modified cluster labels array.
    """
    if source == destination:
        return

    n_clusters = labels.max(initial=-1) + 1
    old_values = list(range(n_clusters))
    new_values = old_values.copy()

    # Moving up
    if source > destination:
        del new_values[source:source + count]
        new_values[destination:destination] = old_values[source:source + count]
    # Moving down
    else:
        new_values[destination:destination] = old_values[source:source + count]
        del new_values[source:source + count]

    return remap_clusters(labels, old_values, new_values, in_place=in_place)


def remap_clusters(labels: np.ndarray, old_values: typing.Union[list[int], tuple[int]], new_values: typing.Union[list[int], tuple[int]], in_place=False):
    """
    Replace label values in labels with new values, by projecting old_values -> new_values. All values are int.

    :param labels: 1d NumPy array containing cluster labels [0, N)
    :param old_values: old values to find and replace
    :param new_values: new values to replace with, old_values and new_values should have same length
    :param in_place:
    :return:
    """

    if in_place:
        old_labels = labels.copy()
        new_labels = labels
    else:
        old_labels = labels
        new_labels = labels.copy()

    if len(old_values) != len(new_values):
        raise ValueError(f"Cannot remap labels, because old_values {len(old_values)} is not the same length as {len(new_values)}")

    for i in range(len(old_values)):
        ov = old_values[i]
        nv = new_values[i]
        if ov == nv:
            continue
        new_labels[old_labels == ov] = nv

    return new_labels
