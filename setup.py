import numpy
from setuptools import setup
from Cython.Build import cythonize

setup(
    name='Spike Sorting',
    ext_modules=cythonize("spikedetect_utils.pyx", annotate=True),
    include_dirs=[numpy.get_include()]
)
