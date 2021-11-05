import typing
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


def cluster(data: typing.Union[np.ndarray, SpikeFeatures, list[SpikeFeatures]], n_clusters=3, method='kmeans'):
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


def split_cluster(data, labels: np.ndarray, indices: typing.Union[int, list[int], tuple[int]], n_clusters=3, method='kmeans', in_place=False) -> np.ndarray:
    # Sub-cluster on specific clusters
    if type(indices) is int:
        is_sub_data = labels == indices
    else:
        is_sub_data = np.isin(labels, indices)
    sub_labels = cluster(data[is_sub_data], n_clusters=n_clusters, method=method)

    # Shift sub-cluster labels so they don't overlap with original labels
    n_super_clusters = labels.max(initial=-1) + 1
    # n_sub_clusters = sub_labels.max(initial=-1) + 1
    sub_labels += n_super_clusters

    # Write to original array, or a new copy if in_place=False
    out_labels = labels if in_place else labels.copy()
    out_labels[is_sub_data] = sub_labels
    return out_labels

