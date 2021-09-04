import math
import time

import numpy as np

from continuousdata import BlackrockContinuousData
import spikedetect

file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy8\daisy8_20210708\daisy8_20210708.ns5 '
cont_data = BlackrockContinuousData()
cont_data.read(file, n_samples=30000, electrodes=None)

spike_data = spikedetect.find_waveforms(cont_data, direction=-1, n_sigmas=2.0, n_sigmas_reject=40.0,
                                        n_sigmas_return=1.0)
