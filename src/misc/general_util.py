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
from typing import Callable


class __VerbosePrint:
    __verbose = False

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, value):
        self.__verbose = value

    @verbose.deleter
    def verbose(self):
        del self.__verbose

    @classmethod
    def vprint(cls, *args, **kwargs):
        if cls.verbose:
            eprint(*args, **kwargs)


def eprint(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    __VerbosePrint.vprint(*args, **kwargs)


def interleave(x: list, y: list) -> list:
    out = [x for xs in zip(x, y) for x in xs]
    return out


def deinterleave(y: list) -> list:
    y = [y[i::2] for i in range(2)]
    return y[0] + y[1]


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
