import math

import numpy as np
import pytest
from scipy.signal import resample

import dsp.demodulation as dsp

EPSILON = 1e-12


@pytest.fixture
def data():
    inp = [0j, 1 + 2j, 2 + 3j, 3 + 4j, 4 + 5j, 5 + 6j, 6 + 7j, 7 + 8j]
    outp = np.empty(len(inp), dtype=np.floating)
    return np.reshape(inp, (1, len(inp))), np.empty(shape=(1, len(inp)), dtype=np.floating)


def test_fm(data):
    inp, outp = data
    dsp.fmDemod(np.array(inp), outp)
    testOutp = [0] * (inp.shape[1] >> 1)
    for i in range(0, inp.shape[1], 2):
        temp = inp[0][i] * inp[0][i + 1].conjugate()
        testOutp[i >> 1] = math.atan2(temp.imag, temp.real)
    testOutp = resample(testOutp, inp.shape[1])
    for x, y in zip(outp[0], testOutp):
        assert math.fabs(x - y) < EPSILON


def test_am(data):
    inp, outp = data
    dsp.amDemod(np.array(inp), outp)
    testOutp = [math.sqrt(math.pow(z.real, 2) + math.pow(z.imag, 2)) for z in inp[0]]
    for x, y in zip(outp[0], testOutp):
        assert math.fabs(x - y) < EPSILON


def test_imag(data):
    inp, outp = data
    dsp.imagOutput(np.array(inp), outp)
    for x, z in zip(outp[0], inp[0]):
        assert x == z.imag


def test_real(data):
    inp, outp = data
    dsp.realOutput(np.array(inp), outp)
    for x, z in zip(outp[0], inp[0]):
        assert x == z.real
