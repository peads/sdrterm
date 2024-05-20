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
import sys
import traceback
from numbers import Number
from typing import Callable

import numpy as np


class __VerbosePrint:
    __verbose = False
    __trace = False

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, value):
        self.__verbose = value

    @verbose.deleter
    def verbose(self):
        del self.__verbose

    @property
    def trace(self):
        return self.__trace

    @trace.setter
    def trace(self, value):
        self.__verbose = self.__trace = value

    @trace.deleter
    def trace(self):
        del self.__trace

    @classmethod
    def vprint(cls, *args, **kwargs):
        if cls.verbose:
            eprint(*args, **kwargs)

    @classmethod
    def tprint(cls, *args, **kwargs):
        if cls.trace:
            eprint(*args, **kwargs)


def eprint(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs):
    __VerbosePrint.tprint(*args, **kwargs)


def interleave(x: list, y: list) -> list:
    out = [x for xs in zip(x, y) for x in xs]
    return out


# def convertDeinterlRealToComplex(y: np.ndarray[any, np.real]) -> np.ndarray:
#     return np.array([re + 1j * im for re, im in zip(y[:len(y) // 2], y[len(y) // 2:])])
#
#
# def deinterleave(y: list) -> list:
#     y = [y[i::2] for i in range(2)]
#     return y[0] + y[1]


def deinterleave(y: list[Number] | np.ndarray[any, np.number]) -> np.ndarray[any, np.complex_]:
    y = [a + 1j * b for a, b in zip(y[::2], y[1::2])]
    return np.array(y)


def printException(e):
    eprint(f'Error: {e}')
    traceback.print_exc(file=sys.stderr)


def applyIgnoreException(func: Callable[[], None]):
    try:
        func()
    except Exception:
        pass


def setVerbose(verbose: bool):
    __VerbosePrint.verbose = verbose


def setTrace(trace: bool):
    __VerbosePrint.trace = trace


def poolErrorCallback(value):
    eprint(value)
