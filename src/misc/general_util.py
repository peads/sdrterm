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
from contextlib import closing
from sys import stderr
from types import FrameType
from typing import Callable, TextIO


class __VerbosePrint:
    @staticmethod
    def vprint(*args, **kwargs) -> None:
        pass

    @staticmethod
    def tprint(*args, **kwargs) -> None:
        pass


def eprint(*args, func: Callable[[any, TextIO, any], None] = lambda *a, **k: print(*a, file=stderr, **k), **kwargs) -> None:
    func(*args, **kwargs)


def vprint(*args, **kwargs) -> None:
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs) -> None:
    __VerbosePrint.tprint(*args, **kwargs)


def printException(e: Exception | BaseException, *args) -> None:
    from traceback import print_exc
    eprint(e, *args)
    print_exc(file=stderr)


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


def shutdownSocket(*socks: socket.socket) -> None:
    for sock in socks:
        __applyIgnoreException(lambda: sock.send(b''), lambda: sock.shutdown(socket.SHUT_RDWR))


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost') -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def __extendSignalHandlers(pid: int, handlers: dict, func: Callable[[int], None]) \
        -> Callable[[int, FrameType | None], None]:

    def handlePostSignal(sig: int):
        from os import kill, name
        func(sig)
        tprint(f'Post handler got: {s.Signals(sig).name}')
        if 'posix' in name:
            from os import killpg, getpgid
            pgid = getpgid(pid)
            # sig = s.SIGINT if s.SIGTERM == sig else sig
            tprint(f'Post handler throwing: {s.Signals(sig).name} to process group {pgid}')
            killpg(pgid, sig)
        tprint(f'Post handler rethrowing: {s.Signals(sig).name}')
        kill(pid, sig)

    def handleSignal(sig: int, frame: FrameType):
        tprint(f'Frame: {frame}\nCaught signal: {s.Signals(sig).name}')
        if sig in handlers.keys():
            newHandler = handlers.pop(sig)
            s.signal(sig, newHandler)
            tprint(f'Reset signal handler from {handleSignal} back to {newHandler}')
        tprint(f'Handlers after processing: {handlers}')
        handlePostSignal(sig)

    return handleSignal


def setSignalHandlers(pid: int, func: Callable[[int], None]):
    from os import name
    signals = [s.SIGINT, s.SIGTERM, s.SIGABRT]
    handlers = {}
    if 'posix' in name:
        signals.append(s.SIGQUIT)
    elif 'nt' in name:
        signals.append(s.SIGBREAK)

    for sig in signals:
        handlers[sig] = s.getsignal(sig)
        s.signal(sig, __extendSignalHandlers(pid, handlers, func))
