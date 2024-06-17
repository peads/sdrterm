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


def fmDemod(data: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
    u = data[0::2]
    v = np.conj(data[1::2])
    if len(u) < len(v):
        u = np.append(u, 0)
    elif len(v) < len(u):
        v = np.append(v, 0)
    u = u * v
    return signal.resample(np.angle(u), len(data))


def amDemod(data: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
    return np.abs(data)


def realOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.real(data)


def imagOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.imag(data)


def absFftOutput(data: np.ndarray[any, np.complex64 | np.complex128]) -> ndarray[any, np.real]:
    return np.abs(fft.fft(data))
