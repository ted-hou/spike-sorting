import math
import warnings

import numpy
import numpy as np


def haar_transform(x: numpy.ndarray, h: numpy.ndarray = None, orthogonal=True):
    """
    Perform 1-d discrete Haar wavelet transform.
    :param x: input signal with shape (n_signals, n_samples_per_signal)
    :param h: (optional) Haar transformation matrix. Provide cached matrix for performance.
    :param orthogonal: orthogonal transformation is likely slower (default True)
    :return:
    """

    x = np.asarray(x, dtype=np.float64)

    n_samples = x.shape[1]

    # Ensure n_samples is power of two by padding data
    if not _is_power_of_two(n_samples):
        x = _conform_shape_to_pow2(x, axis=1, mode='rpad', pad_with='median')
        n_samples = x.shape[1]

    # Calculate Haar matrix
    if h is None:
        h = haar_matrix(n_samples, orthogonal)

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


def _is_power_of_two(n: int):
    return n != 0 and (n & (n - 1) == 0)


def _conform_shape_to_pow2(data: np.ndarray, axis=0, mode='lrtrim', pad_with='median'):
    """
    Ensure data length is power of two along a specific axis.

    :param data: input data
    :param axis: (default 0)
    :param mode: 'rtrim', 'ltrim', 'lrtrim', 'rpad', 'lpad', 'lrpad' (default 'lrtrim')
    :param pad_with: 'median', 'mean', or 'constant' (use zeros). See numpy.pad() (default 'median')
    :return:
    View of sliced array (trim mode) or copy of padded array (pad mode)
    """

    data_length = data.shape[axis]
    if data_length <= 1:
        raise ValueError(f"Data length expected to be 2 or higher, is {data_length}")
    elif _is_power_of_two(data_length):
        return data
    else:
        if mode in ('rtrim', 'ltrim', 'lrtrim'):
            desired_length = 2 ** math.floor(math.log2(data_length))
        elif mode in ('lpad', 'rpad', 'lrpad'):
            desired_length = 2 ** math.ceil(math.log2(data_length))
        else:
            raise ValueError(
                f"Unrecognized mode: '{mode}', expected 'rtrim', 'ltrim', 'lrtrim', 'lpad', 'rpad', or 'lrpad'")

    if mode == 'rtrim':
        data = data.take(range(0, desired_length), axis=axis)
    elif mode == 'ltrim':
        data = data.take(range(data_length - desired_length, data_length), axis=axis)
    elif mode == 'lrtrim':
        n_ltrim = (data_length - desired_length) // 2
        n_rtrim = data_length - desired_length - n_ltrim
        data = data.take(range(n_ltrim, data_length - n_rtrim), axis=axis)
    elif mode == 'rpad':
        pw = [(0, 0)] * data.ndim
        pw[axis] = (0, desired_length - data_length)
        data = np.pad(data, pad_width=pw, mode=pad_with)
    elif mode == 'lpad':
        pw = [(0, 0)] * data.ndim
        pw[axis] = (desired_length - data_length, 0)
        data = np.pad(data, pad_width=pw, mode=pad_with)
    elif mode == 'lrpad':
        n_lpad = (desired_length - data_length) // 2
        n_rpad = desired_length - data_length - n_lpad
        pw = [(0, 0)] * data.ndim
        pw[axis] = (n_lpad, n_rpad)
        data = np.pad(data, pad_width=pw, mode=pad_with)

    assert data.shape[axis] == desired_length
    return data