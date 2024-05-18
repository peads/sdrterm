#
# This file is part of the sdrterm distribution
# (https://github.com/peads/sdrterm).
# with code originally part of the demodulator distribution
# (https://github.com/peads/demodulator).
# Copyright (c) 2023-2024 Patrick Eads.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
from numbers import Complex, Number, Real

import numpy as np
from scipy import signal


def convertDeinterlRealToComplex(y: list[Number] | np.ndarray[any, np.real]) -> \
        np.ndarray[any, np.complex_]:
    return np.array([re + 1j * im for re, im in zip(y[:len(y) // 2], y[len(y) // 2:])])


def shiftFreq(y: np.ndarray[any, np.complex_] | list[Complex], freq: Real, fs: Real) -> np.ndarray[
    any, np.complex_]:
    if not freq or not fs:
        return y
    t = np.arange(len(y))
    # shift in frequency specified in Hz
    shift = np.exp(-2j * np.pi * (freq / fs) * t)

    return y * shift


def applyFilters(y: np.ndarray, filters: list[np.ndarray]) -> np.ndarray:
    for sos in filters:
        y = signal.sosfilt(sos, y)
    return y


def generateDeemphFilter(fs: Real, f=7.5e-5) -> np.ndarray[any, np.number]:
    alpha = 1 / (1 - np.exp(-26666.7 / (f * fs)))
    B = [alpha, 1]
    A = [1]
    return signal.tf2sos(B, A)


def generateInputFilters(fs: float, deg: int, omega: Number | np.number):
    # return signal.ellip(deg, 1, 30, [1, omega],
    return signal.butter(deg, [1, omega],
                         btype='bandpass',
                         analog=False,
                         output='sos',
                         fs=fs)


def generateFmInputFilters(fs: float, deg: int, omega: Number | np.number = 12500):
    return generateInputFilters(fs, deg, omega)


def generateAmInputFilters(fs: float, deg: int, omega: Number | np.number = 10000):
    return generateInputFilters(fs, deg, omega)


def generateBroadcastOutputFilter(fs: float, deg: int, omega=18000):
    # return signal.ellip(deg, 1, 30, omega,
    return signal.butter(deg, omega,
                         btype='lowpass',
                         analog=False,
                         output='sos',
                         fs=fs)


def generateFmOutputFilters(fs: float, deg: int, omega: int) -> list[np.ndarray]:
    return [generateDeemphFilter(fs), generateBroadcastOutputFilter(fs, deg, omega)]


def normalize(x: np.ndarray | list[Number]) -> np.ndarray[np.number] | list[Number]:
    if x is None:
        raise ValueError('x is None')

    x = np.array(x)

    # def f(a, b):
    #     return (b - a) * (x - xmin) / (xmax - xmin) + a

    # return f(-0.5, 0.5)
    return (x - x.min()) / (x.max() - x.min()) - 0.5


def cnormalize(Z: np.ndarray[any, np.complex_]) -> np.ndarray[any, np.complex_]:
    ret = Z / np.abs(Z)
    ix = np.isnan(ret[:, ])
    ret[ix] = ret[np.ix_(ix)].all(0)
    return ret


def rms(inp):
    def func(a):
        return np.sqrt(-np.square(np.sum(a)) + len(a) * np.sum(a * a)) / len(a)

    ret = np.apply_along_axis(func, -1, inp)
    return ret


def generateDomain(dataType: str):
    xmin, xmax = None, None
    match dataType:
        case 'B':
            xmin, xmax = 0, 255
        case 'b':
            xmin, xmax = -128, 127
        case 'H':
            xmin, xmax = 0, 65536
        case 'h':
            xmin, xmax = -32768, 32767
        case 'I':
            xmin, xmax = 0, 4294967295
        case 'i':
            xmin, xmax = -2147483648, 2147483647
        case 'L':
            xmin, xmax = 0, 18446744073709551615
        case 'l':
            xmin, xmax = -9223372036854775808, 9223372036854775807
        case _:
            pass
    return xmin, xmax
