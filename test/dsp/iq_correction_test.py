import numpy as np
import pytest

# from dsp.iq_correction import IQCorrection

DEFAULT_SAMPLE_RATE = 2000
DEFAULT_IMPEDANCE = 50
NEXT_SAMPLE_RATE = 3750
NEXT_IMPEDANCE = 75


@pytest.fixture
def corrector():
    try:
        from dsp.fast import iq_correction
        print('Imported pre-compiled IQCorrection class')
        return iq_correction.IQCorrection(DEFAULT_SAMPLE_RATE)
    except ImportError:
        return None


def test_iqCorrection(corrector):
    if corrector is not None:
        someData = np.array([0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j])
        offset = np.array([0j])
        off = np.array(0j)
        someCorrectedData = np.array(someData)
        inductance = NEXT_IMPEDANCE / NEXT_SAMPLE_RATE

        for j in range(someData.shape[0]):
            someCorrectedData[j] -= off
            off += someCorrectedData[j] * inductance

        assert corrector.fs == DEFAULT_SAMPLE_RATE
        assert corrector.inductance == DEFAULT_IMPEDANCE / DEFAULT_SAMPLE_RATE

        corrector.fs = NEXT_SAMPLE_RATE
        assert corrector.fs == NEXT_SAMPLE_RATE
        assert corrector.inductance == DEFAULT_IMPEDANCE / NEXT_SAMPLE_RATE

        corrector.impedance = NEXT_IMPEDANCE
        assert corrector.inductance == inductance

        size = someData.size
        corrector.correctIq(someData, offset)
        assert someData.size == size
        assert someCorrectedData.size == size
        for x, y in zip(someData, someCorrectedData):
            assert np.fabs(np.abs(x - y)) < 10E-2
