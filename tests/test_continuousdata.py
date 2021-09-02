from continuousdata import BlackrockContinuousData
import unittest

# This file has 60 channels (0 -> 59). corresponding to electrodes: [1, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
# 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77,
# 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 96]
file = r'\\research.files.med.harvard.edu\neurobio\NEUROBIOLOGY SHARED\Assad Lab\Lingfeng\Data\daisy8\daisy8_20210708\daisy8_20210708.ns5 '
n_samples = 3000


class TestContinuousData(unittest.TestCase):
    def test_data_shape(self):
        """Check shape of data, must be (n_samples, n_channels)"""
        cd = BlackrockContinuousData()
        cd.read(file, n_samples=n_samples)
        self.assertEqual(cd.n_samples, n_samples)
        self.assertTupleEqual(cd.data.shape, (cd.n_samples, cd.n_channels))

    def test_select_channels(self):
        """When reading a subset of channels, check data corresponds to number of channels"""
        sel_channels = [2, 3, 7]
        cd = BlackrockContinuousData()
        cd.read(file, n_samples=n_samples, channels=sel_channels)
        self.assertEqual(cd.n_channels, len(sel_channels))  # Check data shape

        # Check data equality (read all channels vs. read select channels)
        from numpy.testing import assert_array_equal
        cd_all = BlackrockContinuousData()
        cd_all.read(file, n_samples=n_samples, channels=None)
        assert_array_equal(cd_all.data[:, (2, 3, 7)], cd.data)

    def test_select_partially_unavailable_channels(self):
        """When reading a subset of channels (some exceeding channel count), extra channels (>=60) should not be read"""
        sel_channels = [0, 1, 2, 5, 60, 999]
        cd = BlackrockContinuousData()
        cd.read(file, n_samples=n_samples, channels=sel_channels)
        self.assertNotEqual(cd.n_channels, len(sel_channels))
        self.assertEqual(cd.n_channels, sum([c < 60 for c in sel_channels]))
        self.assertEqual(cd.channels, [c for c in sel_channels if c < 60])

    def test_all_unavailable_channels(self):
        """Read a subset of channels, but none are available"""
        sel_channels = [60, 100, 200, 10000]

        ed = BlackrockContinuousData()
        with self.assertRaises(ValueError):
            ed.read(file, n_samples=n_samples, channels=sel_channels)

    def test_select_electrodes(self):
        """Read a subset of electrodes, then check if those electrodes are read."""
        sel_electrodes = [5, 96]

        ed = BlackrockContinuousData()
        ed.read(file, n_samples=n_samples, electrodes=sel_electrodes)
        self.assertEqual(ed.data.shape[1], len(sel_electrodes))
        self.assertEqual(ed.electrodes, sel_electrodes)
        for ie in sel_electrodes:
            self.assertIn(ie, [ci.electrode_id for ci in ed.channels_info])

    def test_partially_unavailable_electrodes(self):
        """Read a subset of electrodes (some - 2,3,4 - not in datafile), then check if unavailable ones are excluded."""
        sel_electrodes = [1, 2, 3, 4, 5]

        ed = BlackrockContinuousData()
        ed.read(file, n_samples=n_samples, electrodes=sel_electrodes)
        self.assertNotEqual(ed.n_channels, len(sel_electrodes))
        for i in [1, 5]:
            self.assertIn(i, ed.electrodes)
        for i in [2, 3, 4]:
            self.assertFalse(i in ed.electrodes)

    def test_all_unavailable_electrodes(self):
        """Read a subset of electrodes, but none are available"""
        sel_electrodes = [100, 200, 10000]

        ed = BlackrockContinuousData()
        with self.assertRaises(ValueError):
            ed.read(file, n_samples=n_samples, electrodes=sel_electrodes)


if __name__ == '__main__':
    unittest.main()
