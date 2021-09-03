import math

import numpy
import numpy as np

from _dwt_utils import _haart_1d_loop


def haart_1d_loop(x, orthogonal=True):
    y = _haart_1d_loop(np.asarray(x, dtype=np.float64), 1 if orthogonal else 0)
    return np.asarray(y)


def haart_1d(x: numpy.ndarray, h: numpy.ndarray = None, orthogonal=True):
    """
    Perform 1-d discrete Haar wavelet transform.
    :param x: input signal with shape (n_signals, n_samples_per_signal)
    :param h: (optional) Haar transformation matrix. Provide cached matrix for performance.
    :param orthogonal: orthogonal transformation is likely slower (default True)
    :return:
    """

    if h is None:
        h = haar_matrix(x.shape[1], orthogonal)

    y = x @ h.T

    return y, h


def haar_matrix(n=2, orthogonal=True):
    """
    Creates an n x n (optionally orthonormal) Haar transformation matrix. Where n is a power of 2.

    k = log2(n)

    H(k=1) = [[1, 1]
              [1, -1]]

    H(k+1) = [H(k) kron [1, 1]
              2**(k/2) * I(2**k) kron [1, -1]]

    For an orthogonal matrix, H(k) then needs to be normalized by column Euclidean norms.

    Otherwise no normalization is needed and the scaling term 2**(k/2) can be omitted.
    This is equivalent to omitting division by sqrt(2) after calculating pairwise sums and diffs.

    From:
        Steeb, W. H., Hardy, Y., & Stoop, R. (2003). Discrete wavelets and perturbation theory.
        JOURNAL OF PHYSICS-LONDON-A MATHEMATICAL AND GENERAL, 36(24), 6807-6812.
    :param n: matrix size, expected to be power of 2. Otherwise n = 2**np.floor(np.log2(n))
    :param orthogonal: True to request an orthogonal Haar matrix (slower). (default True)
    :return:
    nxn Haar matrix.
    """
    k = int(math.log2(n))
    h = _haar_matrix_recursive(k, orthogonal)

    # Normalize columns (divide by column Euclidean norm)
    if orthogonal:
        h /= np.linalg.norm(h, axis=0)
    return h


def _haar_matrix_recursive(k, orthogonal=True):
    if k > 1:
        h = _haar_matrix_recursive(k - 1, orthogonal)
        # Calculate the top and bottom parts
        h_t = np.kron(h, [1, 1])
        h_b = np.kron(np.eye(2 ** (k - 1)), [1, -1])
        # The orthogonal Haar matrix requires scaling the bottom half
        if orthogonal:
            h_b *= 2 ** ((k - 1) / 2)
        h = np.vstack((h_t, h_b))
    else:
        h = np.asarray([[1, 1], [1, -1]])

    return h
