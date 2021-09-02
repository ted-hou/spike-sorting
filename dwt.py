import math
import numpy as np

from _dwt_utils import _haart_1d_loop


def haart_1d_loop(x):
    y = _haart_1d_loop(np.asarray(x, dtype=np.float64))
    return np.asarray(y)


def haart_1d_mat(x, h=None, norm=True):
    if h is None:
        h = get_haar_matrix(x.shape[1], norm=norm)

    y = x @ h

    return y, h


def get_haar_matrix(n=2, norm=True):
    k = int(math.log2(n))
    return _haar_matrix(k, norm)


def _haar_matrix(k=1, norm=True, _root=True):
    """
    Creates an 2**k by 2**k (normalized or non-normalized) Haar transformation matrix. Where n is a power of 2.

    k = log2(n)

    H(k=1) = [[1, 1]
              [1, -1]]

    H(k+1) = [H(k) kron [1, 1]
              2**(k/2) * I(2**k) kron [1, -1]]

    From:
        Steeb, W. H., Hardy, Y., & Stoop, R. (2003). Discrete wavelets and perturbation theory.
        JOURNAL OF PHYSICS-LONDON-A MATHEMATICAL AND GENERAL, 36(24), 6807-6812.
    :param n: matrix size, expected to be power of 2. Otherwise n = 2**np.floor(np.log2(n))
    :param norm: True for normalized transformation matrix (slower). (default True)
    :return:
    nxn Haar matrix.
    """
    if k > 1:
        h = _haar_matrix(k - 1, norm=norm, _root=False)
        # Calculate the top part
        h_t = np.kron(h, [1, 1])
        # Calculate the bottom part
        h_b = np.kron(np.eye(2 ** (k - 1)), [1, -1])
        if norm:
            h_b *= 2 ** ((k - 1) / 2)
        h = np.vstack((h_t, h_b))
    else:
        h = np.asarray([[1, 1], [1, -1]], dtype=np.float64)

    # Normalize columns (divide by column Euclidean norm)
    if norm and _root:
        h /= np.linalg.norm(h, axis=0)

    return h
