import numpy as np
import pytest

from dsp.iq_correction import IQCorrection

DEFAULT_SAMPLE_RATE = 2000
DEFAULT_IMPEDANCE = 50
NEXT_SAMPLE_RATE = 3750
NEXT_IMPEDANCE = 75


@pytest.fixture
def corrector():
    return IQCorrection(DEFAULT_SAMPLE_RATE)


def test_iqCorrection(corrector):
    assert corrector.sampleRate == DEFAULT_SAMPLE_RATE
    assert corrector.inductance == DEFAULT_IMPEDANCE / DEFAULT_SAMPLE_RATE

    corrector.sampleRate = NEXT_SAMPLE_RATE
    assert corrector.sampleRate == NEXT_SAMPLE_RATE
    assert corrector.inductance == DEFAULT_IMPEDANCE / NEXT_SAMPLE_RATE

    corrector.inductance = NEXT_IMPEDANCE
    assert corrector.inductance == NEXT_IMPEDANCE / NEXT_SAMPLE_RATE

    someData = np.array([0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j])
    offset = 0j
    someCorrectedData = np.array(someData)
    for i, x in enumerate(someCorrectedData):
        someCorrectedData[i] -= offset
        offset += someCorrectedData[i] * corrector.inductance

    size = someData.size
    corrector.correctIq(someData)
    assert someData.size == size
    assert someCorrectedData.size == size
    for x, y in zip(someData, someCorrectedData):
        assert x == y

    assert locals().get('corrector') is not None
    del corrector
    assert locals().get('corrector') is None
