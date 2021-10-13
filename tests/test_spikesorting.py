import unittest
import numpy as np
from continuousdata import BlackrockContinuousData
from spikesorting import *


class TestSpikeSorting(unittest.TestCase):
    def test_reorder_clusters(self):
        # Generate random labels
        n_clusters = 5
        n_waveforms = 1000
        from numpy.random import default_rng
        rng = default_rng()
        labels = rng.integers(low=0, high=n_clusters, size=n_waveforms)
        labels_original = labels.copy()

        # Test re-ordering
        for from_cluster in range(n_clusters):
            for to_cluster in range(n_clusters):
                if from_cluster == to_cluster:
                    continue
                labels = labels_original.copy()
                labels_copy = reorder_clusters(labels, from_cluster, to_cluster, in_place=False)
                labels = labels_original.copy()
                labels_inplace = reorder_clusters(labels, from_cluster, to_cluster, in_place=True)

                # Reordering in-place and returning copy should give same results
                self.assertTrue(np.array_equal(labels_inplace, labels_copy))
                self.assertIs(labels_inplace, labels)
                self.assertIsNot(labels_inplace, labels_copy)

                # Test index shifting
                direction = 1 if from_cluster > to_cluster else -1
                self.assertTrue(np.array_equal(labels_original == from_cluster, labels == to_cluster))
                for i in range(to_cluster, from_cluster, direction):
                    self.assertTrue(np.array_equal(labels_original == i, labels == i + direction))


if __name__ == '__main__':
    unittest.main()
