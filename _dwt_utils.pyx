#cython: wraparound=False
#cython: boundscheck=False
#cython: language_level=3
#cython: profile=True

import numpy as np
cimport numpy as np
from libc.math cimport log2

DEF SQRT2 = 1.414213562373095
def _haart_1d_loop(np.float64_t[:, ::1] x_in, bint orthogonal):
    cdef:
        int n_signals, length, j
        np.float64_t[:, ::1] x, y

    n_signals = x_in.shape[0]
    length = x_in.shape[1]
    length = 2**int(log2(length))

    # Make a copy of the input array
    x = np.empty((n_signals, length), dtype=np.float64)
    x[:] = x_in[:, :length]
    y = np.empty((n_signals, length), dtype=np.float64)

    length = length // 2
    with nogil:
        while True:
            for i in range(n_signals):
                for j in range(length):
                    if orthogonal:
                        y[i, j] = (x[i, 2*j] + x[i, 2*j + 1]) / SQRT2
                        y[i, length + j] = (x[i, 2*j] - x[i, 2*j + 1]) / SQRT2
                    else:
                        y[i, j] = x[i, 2*j] + x[i, 2*j + 1]
                        y[i, length + j] = x[i, 2*j] - x[i, 2*j + 1]
            if length == 1:
                break
            length = length // 2
            x[:] = y

    return y