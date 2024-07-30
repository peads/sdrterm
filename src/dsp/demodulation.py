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
from numba import guvectorize, complex128, float64
from numpy import angle, ndarray, conj, abs, real, imag, dtype, complexfloating, floating, square
from scipy.signal import resample


@guvectorize([(complex128[:], float64[:])], '(n)->(n)',
             nopython=True,
             cache=True,
             boundscheck=False,
             fastmath=True)
def _fmDemod(data: ndarray[any, dtype[complexfloating]], res: ndarray[any, dtype[floating]]):
    for i in range(0, data.shape[0], 2):
        res[i >> 1] = angle(data[i] * conj(data[i + 1]))


def fmDemod(data: ndarray[any, dtype[complexfloating]], tmp: ndarray[any, dtype[floating]]):
    _fmDemod(data, tmp)
    for i in range(tmp.shape[0]):
        tmp[i] = resample(tmp[i][:tmp.shape[1] >> 1], tmp.shape[1])


@guvectorize([(complex128[:], float64[:])], '(n)->(n)',
             nopython=True,
             cache=True,
             boundscheck=False,
             fastmath=True)
def amDemod(data: ndarray[any, dtype[complexfloating]], res: ndarray[any, dtype[floating]]):
    for i in range(data.shape[0]):
        res[i] = abs(square(data[i]))


@guvectorize([(complex128[:], float64[:])], '(n)->(n)',
             nopython=True,
             cache=True,
             boundscheck=False,
             fastmath=True)
def realOutput(data: ndarray[any, dtype[complexfloating]], res: ndarray[any, dtype[floating]]):
    for i in range(data.shape[0]):
        res[i] = real(data[i])


@guvectorize([(complex128[:], float64[:])], '(n)->(n)',
             nopython=True,
             cache=True,
             boundscheck=False,
             fastmath=True)
def imagOutput(data: ndarray[any, dtype[complexfloating]], res: ndarray[any, dtype[floating]]):
    for i in range(data.shape[0]):
        res[i] = imag(data[i])


@guvectorize([(complex128[:], complex128[:, :], complex128[:, :])], '(n),(m,n)->(m,n)',
             nopython=True,
             cache=True,
             boundscheck=False,
             fastmath=True)
def shiftFreq(y: ndarray[any, dtype[complexfloating]],
              shift: ndarray[any, dtype[complexfloating]],
              res: ndarray[any, dtype[complexfloating]]) -> None:
    res[:, :] = y * shift
