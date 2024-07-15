import math

import numpy as np
import pytest
from scipy.signal import resample

import dsp.demodulation as dsp

EPSILON = 1e-12


@pytest.fixture
def data():
    return [0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j]


def test_fm(data):
    outp = dsp.fmDemod(np.array(data))
    testOutp = [0] * (len(data) >> 1)
    for i in range(0, len(data), 2):
        temp = data[i] * data[i + 1].conjugate()
        testOutp[i >> 1] = math.atan2(temp.imag, temp.real)
    testOutp = resample(testOutp, len(data))
    for x, y in zip(outp, testOutp):
        assert math.fabs(x - y) < EPSILON


def test_am(data):
    outp = dsp.amDemod(np.array(data))
    testOutp = [math.sqrt(math.pow(z.real, 2) + math.pow(z.imag, 2)) for z in data]
    for x, y in zip(outp, testOutp):
        assert math.fabs(x - y) < EPSILON


def test_imag(data):
    outp = dsp.imagOutput(np.array(data))
    for x, z in zip(outp, data):
        assert x == z.imag


def test_real(data):
    outp = dsp.realOutput(np.array(data))
    for x, z in zip(outp, data):
        assert x == z.real
