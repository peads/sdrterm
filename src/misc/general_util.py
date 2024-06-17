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
from typing import Callable, Iterable

import numpy as np


class __VerbosePrint:
    @classmethod
    def vprint(cls, *args, **kwargs) -> None:
        pass

    @classmethod
    def tprint(cls, *args, **kwargs) -> None:
        pass


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs) -> None:
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs) -> None:
    __VerbosePrint.tprint(*args, **kwargs)


# def interleave(x: list, y: list) -> list:
#     return [x for xs in zip(x, y) for x in xs]

def deinterleave(y: Iterable[Number] | np.ndarray[any, np.number]) -> np.ndarray[any, np.complex64 | np.complex128] | None:
    return np.array([a + 1j * b for a, b in zip(y[::2], y[1::2])])


def printException(e: Exception) -> None:
    eprint(f'Error: {e}')
    traceback.print_exc(file=sys.stderr)


def __applyIgnoreException(*func: Callable[[], None]) -> None:
    for f in func:
        try:
            f()
        except Exception:
            pass


def verboseOn() -> None:
    setattr(__VerbosePrint, 'vprint', eprint)


def traceOn() -> None:
    verboseOn()
    setattr(__VerbosePrint, 'tprint', eprint)


def initializer(isDead: Condition) -> None:
    def handleSignal(_, __):
        isDead.value = 1

    s.signal(s.SIGINT, handleSignal)


def shutdownSocket(sock: socket.socket) -> None:
    __applyIgnoreException(lambda: sock.send(b''))
    __applyIgnoreException(lambda: sock.shutdown(socket.SHUT_RDWR))


def shutdownSockets(*socks: socket.socket) -> None:
    for sock in socks:
        shutdownSocket(sock)
