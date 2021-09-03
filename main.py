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


waveform = np.tile([5, 3, 2, 6, 10, 8, 11, 11], (1000000, 1))

# Benchmark
n_repeats = 10
n_waveforms = waveform.shape[0]
from dwt import *
tic = time.time()
for _ in range(n_repeats):
    y1 = haart_1d_loop(waveform, True)
print(f"Cython haart_1d_loop(orthogonal=True) x {n_waveforms}x{n_repeats:d} took {time.time() - tic:.4f}s")

tic = time.time()
for _ in range(n_repeats):
    y2 = haart_1d_loop(waveform, False)
print(f"Cython haart_1d_loop(orthogonal=False) x {n_waveforms}x{n_repeats:d} took {time.time() - tic:.4f}s")

tic = time.time()
h = None
for _ in range(n_repeats):
    (y3, h) = haart_1d(waveform, h, orthogonal=True)
print(f"Python haart_1d(orthogonal=True) x {n_waveforms}x{n_repeats:d} took {time.time() - tic:.4f}s")


tic = time.time()
h = None
for _ in range(n_repeats):
    (y4, h) = haart_1d(waveform, h, orthogonal=False)
print(f"Python haart_1d(orthogonal=False) x {n_waveforms}x{n_repeats:d} took {time.time() - tic:.4f}s")

print(np.allclose(y1, y3))
print(np.allclose(y2, y4))