import numpy as np
import pytest

from dsp.iq_correction import IQCorrection

DEFAULT_SAMPLE_RATE = 2000
DEFAULT_IMPEDANCE = 50
NEXT_SAMPLE_RATE = 3750
NEXT_IMPEDANCE = 75


@pytest.fixture
def correctors():
    ret = [IQCorrection(DEFAULT_SAMPLE_RATE), ]
    try:
        from dsp.fast import iq_correction
        print('Imported pre-compiled IQCorrection class')
        ret.append(iq_correction.IQCorrection(DEFAULT_SAMPLE_RATE))
    except ImportError:
        pass
    return ret


def test_iqCorrection(correctors):
    someData = np.array([[0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j],
                         [0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j],
                         [0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j]])
    offset = np.zeros(3, dtype=np.complex128)
    someCorrectedData = np.array(someData)
    inductance = np.array((DEFAULT_IMPEDANCE, NEXT_IMPEDANCE))/ DEFAULT_SAMPLE_RATE
    inductance = np.append(inductance, NEXT_IMPEDANCE / NEXT_SAMPLE_RATE)

    for i in range(someData.shape[0]):
        # someCorrectedData[i][:] = someCorrectedData[i][:] - offset
        for j in range(someData.shape[1]):
            someCorrectedData[i][j] -= offset[i]
            offset[i] += someCorrectedData[i][j] * inductance[i]

    for i, corrector in enumerate(correctors):
        assert corrector.fs == DEFAULT_SAMPLE_RATE
        assert corrector.inductance == DEFAULT_IMPEDANCE / DEFAULT_SAMPLE_RATE

        corrector.fs = NEXT_SAMPLE_RATE
        assert corrector.fs == NEXT_SAMPLE_RATE
        assert corrector.inductance == DEFAULT_IMPEDANCE / NEXT_SAMPLE_RATE

        corrector.impedance = NEXT_IMPEDANCE
        assert corrector.inductance == NEXT_IMPEDANCE / NEXT_SAMPLE_RATE

        size = someData.size
        corrector.correctIq(someData[i])
        assert someData.size == size
        assert someCorrectedData.size == size
        for x, y in zip(someData[i], someCorrectedData[2]):
            assert x == y
