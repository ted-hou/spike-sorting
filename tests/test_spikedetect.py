import unittest
import numpy as np
import spikedetect
from continuousdata import BlackrockContinuousData

file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy8\daisy8_20210708\daisy8_20210708.ns5 '
n_samples = 30000
cd = BlackrockContinuousData()
cd.read(file, n_samples=n_samples)


class TestSpikeDetect(unittest.TestCase):
    def test_cull_waveforms(self):
        # Do two rounds of spike detection, the second round with less stringent conditions (less waveform culling).
        spike_data_1 = spikedetect.find_waveforms(cd, n_sigmas=2.0, n_sigmas_return=1.0, n_sigmas_reject=None)
        spike_data_2 = spikedetect.find_waveforms(cd, n_sigmas=2.0, n_sigmas_return=None, n_sigmas_reject=None)

        n_channels = len(spike_data_1)

        n_waveforms_1 = [sd.waveforms.shape[0] for sd in spike_data_1]
        n_waveforms_2 = [sd.waveforms.shape[0] for sd in spike_data_2]

        n_culled_waveforms = [n_waveforms_2[chn] - n_waveforms_1[chn] for chn in range(n_channels)]
        self.assertGreater(sum(n_culled_waveforms), 0, f"Waveform-culling likely failed, {sum(n_waveforms_1)} waveforms were detected in {n_channels} channels but none were culled.")

        for chn in range(n_channels):
            self.assertGreaterEqual(n_waveforms_2[chn], n_waveforms_1[chn], f"Waveform-culling likely failed on channel {chn}, where stronger spikedetect constraints resulted in {abs(n_waveforms_2[chn] - n_waveforms_1[chn])} additional waveforms.")

            # Test numpy.ndarray.resize did not mess up the data
            if n_waveforms_2[chn] > n_waveforms_1[chn]:
                condition = np.array_equal(spike_data_1[chn].waveforms[0, :], spike_data_2[chn].waveforms[0, :])
                msg = f"Waveform-culling likely failed on channel {chn}, first waveform {spike_data_2[chn].waveforms[0, :]} became {spike_data_1[chn].waveforms[0, :]} after culling. This is likely an error due to using numpy.ndarray.resize on a non-C-ordered NumPy array."
                self.assertTrue(condition, msg)


if __name__ == '__main__':
    unittest.main()
