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
import signal as s
import socket
import sys
import traceback
from multiprocessing import Condition
from numbers import Number
from typing import Callable

import numpy as np


class __VerbosePrint:
    @classmethod
    def vprint(cls, *args, **kwargs):
        pass

    @classmethod
    def tprint(cls, *args, **kwargs):
        pass


def eprint(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs):
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs):
    __VerbosePrint.tprint(*args, **kwargs)


def interleave(x: list, y: list) -> list:
    out = [x for xs in zip(x, y) for x in xs]
    return out


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


def verboseOn():
    setattr(__VerbosePrint, 'vprint', eprint)


def traceOn():
    verboseOn()
    setattr(__VerbosePrint, 'tprint', eprint)


def poolErrorCallback(value):
    eprint(value)


def initializer(isDead: Condition):
    def handleSignal(_, __):
        isDead.value = 1
        # raise KeyboardInterrupt
    s.signal(s.SIGINT, handleSignal)


def prevent_out_of_context_execution(method):
    def decorator(self, *args, **kwargs):
        if not self._inside_context:
            raise AttributeError(f"{method.__name__} may only be invoked from inside context.")
        return method(self, *args, **kwargs)

    return decorator


def remove_context(method):
    def decorator(self, *args, **kwargs):
        self._inside_context = False
        self._barrier.abort()
        return method(self, *args, **kwargs)

    return decorator


def closeSocket(clientSckt):
    applyIgnoreException(lambda: clientSckt.send(b''))
    applyIgnoreException(lambda: clientSckt.shutdown(socket.SHUT_RDWR))
    applyIgnoreException(clientSckt.close)
