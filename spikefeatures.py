import warnings
import numpy as np
from scipy import stats
import dwt
from spikedata import SpikeData
from abc import abstractmethod, ABC


class SpikeFeatures(ABC):
    features: np.ndarray  # np.ndarray with shape (n_waveforms, ndims)
    ndims: int
    sorted: bool

    def __init__(self, data):
        self.sorted = False

    @abstractmethod
    def reduce(self, ndims=10):
        pass

    @staticmethod
    def _validate_data_type(data):
        if isinstance(data, SpikeData):
            data = data.waveforms
        if not isinstance(data, np.ndarray):
            raise TypeError(f"data is {type(data)}, expected SpikeData or numpy.ndarray.")
        return data


class SpikeFeaturesPCA(SpikeFeatures):
    pass


class SpikeFeaturesDWT(SpikeFeatures):
    transform_matrix: np.ndarray

    def reduce(self, ndims=10):
        """Select informative features via KS test (least normal => *probably* easily separable)."""

        if self.sorted and ndims >= self.ndims:
            warnings.warn(f"No sorting was performed - features were already sorted.")
            return

        if ndims > self.ndims:
            warnings.warn(f"ndims ({ndims}) is capped at data length ({self.ndims}).")
            ndims = self.ndims

        n_features = self.features.shape[1]

        d = np.empty((n_features,), dtype=np.float64)
        for i_feature in range(n_features):
            x = self.features[:, i_feature]

            # Normalize data and discard outliers (3 sigma)
            x = (x - x.mean()) / x.std()
            # x = x[np.abs(x) <= 3]

            # K-S test against N(0, 1)
            d[i_feature], _ = stats.kstest(x, 'norm', alternative='two-sided')

        # Sort by K-S statistic (less normal/larger K-S statistic ~= more easily separable)
        i_sort = np.argsort(d)
        self.features = self.features[:, i_sort[-ndims:]]
        self.ndims = ndims
        self.sorted = True


class SpikeFeaturesDb4(SpikeFeaturesDWT):
    pass


class SpikeFeaturesHaar(SpikeFeaturesDWT):
    orthogonal: bool
    shape_conform_mode: str
    shape_conform_pad_value: str

    def __init__(self, data, orthogonal=True, shape_conform_mode='rpad', shape_conform_pad_value='median'):
        """
        :param data: SpikeData object or np.ndarray with shape (n_waveforms, n_samples_per_waveform)
        :param orthogonal: orthogonal transformation is likely slower (default True)
        :param shape_conform_mode: how to handle data lengths that aren't powers of two. Can be 'rtrim', 'ltrim', 'lrtrim', 'rpad', 'lpad', 'lrpad' (default 'rpad')
        :param shape_conform_pad_value: what value to use if shape_conform_mode is '*pad'. Can be 'median', 'mean', or 'constant' (use zeros). (default 'median')
        """

        super().__init__(data)
        data = SpikeFeatures._validate_data_type(data)

        self.features, self.transform_matrix = dwt.haar_transform(data, orthogonal=orthogonal,
                                                                  shape_conform_mode=shape_conform_mode,
                                                                  shape_conform_pad_value=shape_conform_pad_value)
        self.orthogonal = orthogonal
        self.shape_conform_mode = shape_conform_mode
        self.shape_conform_pad_value = shape_conform_pad_value
        self.ndims = self.features.shape[1]
