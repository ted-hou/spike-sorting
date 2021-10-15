import unittest
import numpy as np
from continuousdata import BlackrockContinuousData
from spikesorting import *


class TestReorderClusters(unittest.TestCase):
    n_clusters = 6
    n_waveforms = 10000

    @staticmethod
    def _generate_clusters(n_clusters, n_waveforms):
        rng = np.random.default_rng()
        labels = rng.integers(n_clusters, size=n_waveforms)
        return labels

    def test_remap_clusters_in_place(self):
        # Generate cluster labels
        labels_original = self._generate_clusters(self.n_clusters, self.n_waveforms)
        labels = labels_original.copy()

        old_values = list(range(self.n_clusters))
        new_values = list(np.random.permutation(old_values))

        # Test remapping in place
        labels_remapped_inplace = remap_clusters(labels, old_values, new_values, in_place=True)
        self.assertIs(labels_remapped_inplace, labels)
        for i in range(self.n_clusters):
            self.assertTrue(np.array_equal(labels_remapped_inplace == new_values[i], labels_original == old_values[i]))

    def test_remap_clusters(self):
        labels_original = self._generate_clusters(self.n_clusters, self.n_waveforms)
        labels = labels_original.copy()

        old_values = list(range(self.n_clusters))
        new_values = list(np.random.permutation(old_values))

        # Test remapping, returning new array
        labels_remapped = remap_clusters(labels, old_values, new_values, in_place=False)
        self.assertIsNot(labels_remapped, labels)
        for i in range(self.n_clusters):
            self.assertTrue(np.array_equal(labels_remapped == new_values[i], labels_original == old_values[i]))

    def test_move_clusters(self):
        # Generate random labels
        labels_original = self._generate_clusters(self.n_clusters, self.n_waveforms)
        labels = labels_original.copy()

        for source in range(self.n_clusters):
            for count in range(1, self.n_clusters - source):
                for destination in range(self.n_clusters):
                    if source == destination:
                        continue
                    if destination in range(source, source + count):
                        continue

                    labels_moved = move_clusters(labels, source, count, destination)

                    old_values = list(range(self.n_clusters))
                    new_values = old_values.copy()
                    moved_values = old_values[source:source + count]
                    # Moving up/left
                    if source > destination:
                        del new_values[source:source + count]
                        new_values[destination:destination] = moved_values
                    # Moving down/right
                    else:
                        new_values[destination:destination] = moved_values
                        del new_values[source:source + count]

                    for i in range(self.n_clusters):
                        self.assertTrue(np.array_equal(labels_moved == new_values[i], labels_original == old_values[i]))


if __name__ == '__main__':
    unittest.main()
