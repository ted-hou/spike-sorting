import math
import time

import numpy as np

# from continuousdata import BlackrockContinuousData
# import spikedetect
#
# file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy8\daisy8_20210708\daisy8_20210708.ns5 '
# cont_data = BlackrockContinuousData()
# cont_data.read(file, n_samples=30000, electrodes=None)
#
# spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0,
#                                         n_sigmas_return=1.0)


SQRT2 = math.sqrt(2)


def haart_1d_py(signal: np.ndarray) -> np.ndarray:
    out_signal = np.empty(signal.shape, dtype=float)
    in_signal = np.array(signal, dtype=np.float64, copy=True)
    length = in_signal.shape[1] // 2
    while True:
        for i in range(length):
            out_signal[:, i] = (in_signal[:, i * 2] + in_signal[:, i * 2 + 1]) / SQRT2
            out_signal[:, length + i] = (in_signal[:, i * 2] - in_signal[:, i * 2 + 1]) / SQRT2
        if length == 1:
            return out_signal
        length = length // 2
        np.copyto(in_signal, out_signal, casting='no')


waveform = np.tile([5, 3, 2, 6, 10, 8, 11, 11], (100, 1))

# Benchmark
from dwt import *
n_repeats = 100000
tic = time.time()
for _ in range(n_repeats):
    haart_1d_py(waveform)
print(f"Python haart_1d_py() x {n_repeats:d} took {time.time() - tic:.4f}s")

tic = time.time()
for _ in range(n_repeats):
    haart_1d_loop(waveform)
print(f"Cython haart_1d_loop() x {n_repeats:d} took {time.time() - tic:.4f}s")

tic = time.time()
h = None
for _ in range(n_repeats):
    (y, h) = haart_1d_mat(waveform, h, norm=True)
print(f"Python haart_1d_mat() x {n_repeats:d} took {time.time() - tic:.4f}s")

