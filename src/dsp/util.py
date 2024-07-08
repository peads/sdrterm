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
from typing import Iterable

from numpy import ndarray, complex64, complex128, dtype, exp, float32, float64
from scipy.signal import sosfilt, tf2sos, ellip


def applyFilters(y: ndarray | Iterable, *filters) -> ndarray[any, dtype[float32 | float64 | complex64 | complex128]]:
    for sos in filters:
        y = sosfilt(sos, y)
    return y


def generateDeemphFilter(fs: float, f: float = 7.5e-5) -> ndarray[any, dtype[float32 | float64]]:
    alpha = 1 / (1 - exp(-26666.7 / (f * fs)))
    B = [alpha, 1]
    A = [1]
    return tf2sos(B, A)


def generateEllipFilter(fs: int, deg: int, Wn: float | Iterable[float], btype: str) -> tuple[any, float, any]:
    return ellip(deg, 1, 30, Wn,
                 btype=btype,
                 analog=False,
                 output='sos',
                 fs=fs)

# def generateDcBlock():
#     return tf2sos([1, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, .95], analog=False)


# def normalize(x: ndarray | list[Number]) -> ndarray[number] | list[Number]:
#     if x is None:
#         raise ValueError('x is None')
#
#     x = array(x)
#
#     # def f(a, b):
#     #     return (b - a) * (x - xmin) / (xmax - xmin) + a
#
#     # return f(-0.5, 0.5)
#     return (x - x.min()) / (x.max() - x.min()) - 0.5

# def rms(inp):
#     def func(a):
#         return sqrt(-square(sum(a)) + len(a) * sum(a * a)) / len(a)
#
#     ret = apply_along_axis(func, -1, inp)
#     return ret


# def generateDomain(dataType: str):
#     xmin, xmax = None, None
#     match dataType:
#         case 'B':
#             xmin, xmax = 0, 255
#         case 'b':
#             xmin, xmax = -128, 127
#         case 'H':
#             xmin, xmax = 0, 65536
#         case 'h':
#             xmin, xmax = -32768, 32767
#         case 'I':
#             xmin, xmax = 0, 4294967295
#         case 'i':
#             xmin, xmax = -2147483648, 2147483647
#         case 'L':
#             xmin, xmax = 0, 18446744073709551615
#         case 'l':
#             xmin, xmax = -9223372036854775808, 9223372036854775807
#         case _:
#             pass
#     return xmin, xmax
