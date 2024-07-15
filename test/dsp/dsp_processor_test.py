import math

import dsp.dsp_processor as dsp
import dsp.demodulation as dem
import pytest
import numpy as np
from misc.general_util import eprint
DEFAULT_FS = 48000

@pytest.fixture
def processor():
    return dsp.DspProcessor(DEFAULT_FS, omegaOut=250)

@pytest.fixture
def shiftProc():
    return dsp.DspProcessor(DEFAULT_FS, omegaOut=2500, center=-1500)

def test_init(processor):
    assert processor.fs == DEFAULT_FS
    assert processor.decimation == 2
    assert processor.decimatedFs == DEFAULT_FS/2
    processor.selectOuputFm()
    assert processor._demod == dem.fmDemod
    processor.selectOuputWfm()
    assert processor._demod == dem.fmDemod
    processor.selectOuputAm()
    assert processor._demod == dem.amDemod

    with pytest.raises(ValueError) as e:
        processor.decimation = 1
    eprint(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(TypeError) as e:
        processor.decimatedFs = 1
    eprint(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(ValueError) as e:
        processor._setDemod(None, ())
    eprint(f'\n{e.type.__name__}: {e.value}')

    with pytest.raises(TypeError) as e:
        processor._setDemod("asdf", None)
    eprint(f'\n{e.type.__name__}: {e.value}')

    processor.decimation = 3
    assert processor.decimation == 3
    assert processor.decimatedFs == DEFAULT_FS/3

    processor.centerFreq = -1000
    assert processor.centerFreq == -1000

def test_shift(shiftProc):
    shiftProc._generateShift(8)
    assert len(shiftProc._shift)
    for k in range(8):
        assert shiftProc._shift[k] == np.pow(math.e, -2j * math.pi * (shiftProc.centerFreq / shiftProc.fs) * k)
