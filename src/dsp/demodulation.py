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
from numba import njit
from numpy import angle, ndarray, conj, abs, real, imag, dtype, complexfloating, floating
from scipy.signal import resample


@njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, parallel=True)
def _fmDemod(data: ndarray[any, dtype[complexfloating]]) -> ndarray[any, dtype[complexfloating]]:
    return angle(data[::2] * conj(data[1::2]))


def fmDemod(data: ndarray[any, dtype[complexfloating]]) -> ndarray[any, dtype[floating]]:
    # re: ndarray[any, dtype[complex64 | complex128]] = data[0::2]
    # im: ndarray[any, dtype[complex64 | complex128]] = data[1::2]
    # re = re * conj(im)
    # np.reshape(data, (2, data.size >> 1))
    return resample(_fmDemod(data), len(data))


@njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, parallel=True)
def amDemod(data: ndarray[any, dtype[complexfloating]]) -> ndarray[any, dtype[floating]]:
    return abs(data)


@njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, parallel=True)
def realOutput(data: ndarray[any, dtype[complexfloating]]) -> ndarray[any, dtype[floating]]:
    return real(data)


@njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, parallel=True)
def imagOutput(data: ndarray[any, dtype[complexfloating]]) -> ndarray[any, dtype[floating]]:
    return imag(data)


@njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, parallel=True)
def shiftFreq(y: ndarray[any, dtype[complexfloating]],
              shift: ndarray[any, dtype[complexfloating]],
              res: ndarray[any, dtype[complexfloating]]) -> None:
    """
         NOTE: apparently, numpy doesn't override the unary multiplication arithemetic assignment operator the
         same way as the binary multiplication operator for ndarrays. So, this has to remain this way.
     """
    res[:] = y * shift
