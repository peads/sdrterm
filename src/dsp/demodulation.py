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
from numpy import angle, ndarray, conj, abs, real, imag, dtype, complex64, complex128, float32, float64
from scipy.signal import resample


def fmDemod(data: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
    re: ndarray[any, dtype[complex64 | complex128]] = data[0::2]
    im: ndarray[any, dtype[complex64 | complex128]] = data[1::2]
    re = re * conj(im)
    return resample(angle(re), len(data))


def amDemod(data: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
    return abs(data)


def realOutput(data: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
    return real(data)


def imagOutput(data: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
    return imag(data)

# def spectrumOutput(data: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
#     return abs(fft(data))
