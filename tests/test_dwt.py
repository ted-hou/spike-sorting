import unittest
from dwt import _conform_shape_to_pow2
from dwt import *


class TestDWT(unittest.TestCase):
    def test_haar_transform(self):
        data = np.asarray([[1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]])
        data_transformed_ground_truth = [22, -4, -5.65685424949238, 2.82842712474619, -2, -2, 4, 0, -0.707106781186548, -0.707106781186548, -0.707106781186548, -0.707106781186548, -0.707106781186547, -5.55111512312578e-17, -5.55111512312578e-17, -5.55111512312578e-17]
        data_transformed, haar = haar_transform(data)
        self.assertTrue(data_transformed.shape == (3, 16))
        self.assertTrue(np.allclose(data_transformed_ground_truth, data_transformed[1, :]))

    def test_conform_shape_to_pow2(self):
        # for l in range(2, 31):
        l = 14
        reps = 5
        data = np.tile(np.arange(l), (reps, 1))
        l_floor = 2 ** math.floor(math.log2(l))
        l_ceil = 2 ** math.ceil(math.log2(l))

        # lrtrim
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='lrtrim')
        self.assertTrue(data_processed.shape == (reps, l_floor))
        self.assertTrue(data.shape == (reps, l))  # Ensure original array was not modified

        # ltrim
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='ltrim')
        self.assertTrue(data_processed.shape == (reps, l_floor))

        # rtrim
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='rtrim')
        self.assertTrue(data_processed.shape == (reps, l_floor))

        # lpad
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='lpad', pad_with='constant')
        self.assertTrue(data_processed.shape == (reps, l_ceil))
        self.assertTrue(data.shape == (reps, l))  # Ensure original array was not modified

        # rpad
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='rpad', pad_with='constant')
        self.assertTrue(data_processed.shape == (reps, l_ceil))

        # lrpad
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='lrpad', pad_with='constant')
        self.assertTrue(data_processed.shape == (reps, l_ceil))

        # rpad median
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='rpad', pad_with='median')
        self.assertTrue(data_processed.shape == (reps, l_ceil))

        # rpad mean
        data_processed = _conform_shape_to_pow2(data, axis=1, mode='lrpad', pad_with='mean')
        self.assertTrue(data_processed.shape == (reps, l_ceil))


if __name__ == '__main__':
    unittest.main()
