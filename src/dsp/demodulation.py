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

import numpy as np
from numpy import ndarray
from scipy import fft, signal


class __FMDemodulator:
    prevRe: np.complex64 | np.complex128 | None = None
    prevIm: np.complex64 | np.complex128 | None = None

    @classmethod
    def fmDemod(cls, data: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
        re = data[0::2]
        im = data[1::2]

        if cls.prevRe is not None:
            np.insert(re, 0, cls.prevRe)
            cls.prevRe = None
        if cls.prevIm is not None:
            np.insert(im, 0, cls.prevIm)
            cls.prevIm = None

        if len(re) > len(im):
            cls.prevRe = re[-1]
            re = re[:-1]
        elif len(im) > len(re):
            cls.prevIm = im[-1]
            im = im[:-1]
        re = re * np.conj(im)
        return signal.resample(np.angle(re), len(data))


def fmDemod(data: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
    return __FMDemodulator.fmDemod(data)


def amDemod(data: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
    return np.abs(data)


def realOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.real(data)


def imagOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.imag(data)


def spectrumOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.abs(fft.fft(data))
