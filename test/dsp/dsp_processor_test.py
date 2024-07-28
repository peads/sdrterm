import math

import numpy as np
import pytest

import dsp.demodulation as dem
import dsp.dsp_processor as dsp
from dsp.data_processor import DataProcessor

DEFAULT_FS = 48000
DEFAULT_CENTER = -1000
DEFAULT_SHIFT_SIZE = 8
DEFAULT_DECIMATION_FACTOR = 3


@pytest.fixture
def processor():
    return dsp.DspProcessor(DEFAULT_FS, omegaOut=250)


def test_init(processor):
    assert processor.fs == DEFAULT_FS
    assert processor.decimation == 2
    assert processor.decimatedFs == DEFAULT_FS >> 1
    processor.selectOutputFm()
    assert processor.demod == dem.fmDemod
    processor.selectOutputAm()
    assert processor.demod == dem.amDemod

    with pytest.raises(ValueError) as e:
        processor.decimation = 1
    print(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(AttributeError) as e:
        processor.decimatedFs = 1
    print(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(ValueError) as e:
        processor._setDemod(None, ())
    print(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(TypeError) as e:
        processor._setDemod("asdf", None)
    print(f'\n{e.type.__name__}: {e.value}')

    processor.decimation = DEFAULT_DECIMATION_FACTOR
    assert processor.decimation == DEFAULT_DECIMATION_FACTOR
    assert processor.decimatedFs == DEFAULT_FS / DEFAULT_DECIMATION_FACTOR

    processor._generateShift(DEFAULT_SHIFT_SIZE)
    assert processor._shift is None

    processor.centerFreq = DEFAULT_CENTER
    assert processor.centerFreq == DEFAULT_CENTER
    processor._generateShift(DEFAULT_SHIFT_SIZE)
    assert len(processor._shift) == DEFAULT_SHIFT_SIZE
    for k in range(8):
        assert processor._shift[k] == np.pow(math.e, -2j * math.pi * (DEFAULT_CENTER / DEFAULT_FS) * k)

    with pytest.raises(FileNotFoundError) as e:
        processor.processData(None, None, '')
    print(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(AttributeError) as e:
        processor.processData(None, None, None)
    print(f'\n{e.type.__name__}: {e.value}')

    assert locals().get('processor') is not None
    del processor
    assert locals().get('processor') is None

    with pytest.raises(TypeError) as e:
        DataProcessor()
    print(f'\n{e.type.__name__}: {e.value}')
    DataProcessor.processData(None)
