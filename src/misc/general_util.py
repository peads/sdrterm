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
from typing import Callable


class __VerbosePrint:
    @staticmethod
    def vprint(*args, **kwargs) -> None:
        pass

    @staticmethod
    def tprint(*args, **kwargs) -> None:
        pass


def eprint(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


def vprint(*args, **kwargs) -> None:
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs) -> None:
    __VerbosePrint.tprint(*args, **kwargs)


def printException(e: Exception) -> None:
    eprint(f'Error: {e}')
    traceback.print_exc(file=sys.stderr)


def __applyIgnoreException(*func: Callable[[], any]) -> list:
    ret = []
    for f in func:
        try:
            ret.append(f())
        except Exception as e:
            ret.append(e)
    return ret


def verboseOn() -> None:
    setattr(__VerbosePrint, 'vprint', eprint)


def traceOn() -> None:
    verboseOn()
    setattr(__VerbosePrint, 'tprint', eprint)


def initializer(isDead: Condition) -> None:
    def handleSignal(_, __):
        isDead.value = 1

    s.signal(s.SIGINT, handleSignal)


def shutdownSocket(*socks: socket.socket) -> None:
    for sock in socks:
        __applyIgnoreException(lambda: sock.send(b''), lambda: sock.shutdown(socket.SHUT_RDWR))
