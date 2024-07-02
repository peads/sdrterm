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
from contextlib import closing
from os import name as osName
from signal import SIGTERM, SIGABRT, Signals, signal, getsignal, SIGINT
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SHUT_RDWR
from sys import stderr
from types import FrameType
from typing import Callable, TextIO


class __VerbosePrint:
    vlog = lambda *_, **__: None
    tlog = lambda *_, **__: None

    @classmethod
    def vprint(cls, *args, **kwargs) -> None:
        cls.vlog(*args, **kwargs)

    @classmethod
    def tprint(cls, *args, **kwargs) -> None:
        cls.tlog(*args, **kwargs)


def eprint(*args, func: Callable[[any, TextIO, any], None] = lambda *a, **k: print(*a, file=stderr, **k),
           **kwargs) -> None:
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
    __VerbosePrint.vlog = eprint


def traceOn() -> None:
    verboseOn()
    __VerbosePrint.tlog = eprint


def shutdownSocket(*socks: socket) -> None:
    for sock in socks:
        __applyIgnoreException(lambda: sock.send(b''), lambda: sock.shutdown(SHUT_RDWR))


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost') -> int:
    with closing(socket(AF_INET, SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        return s.getsockname()[1]


def killChildren(pid, sig):
    from psutil import Process, NoSuchProcess
    parent = Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        tprint(f'Child status: {child.status()}')
        try:
            child.send_signal(sig)
        except NoSuchProcess:
            pass


def __extendSignalHandlers(pid: int, handlers: dict, handlePostSignal: Callable[[], None]) \
        -> Callable[[int, FrameType | None], None]:
    def handleSignal(sig: int, frame: FrameType):
        tprint(f'Frame: {frame}\npid {pid} caught: {Signals(sig).name}')
        if sig in handlers.keys():
            newHandler = handlers.pop(sig)
            signal(sig, newHandler)
            tprint(f'Reset signal handler from {handleSignal} back to {newHandler}')
        tprint(f'Handlers after processing: {handlers.values()}')
        handlePostSignal()
        if 'posix' not in osName:
            killChildren(pid, sig if sig != SIGINT else SIGTERM)
        else:
            from os import killpg, getpgid
            pgid = getpgid(pid)
            tprint(f'Re-throwing to process group: {pgid}')
            killpg(pgid, sig)

    return handleSignal


def setSignalHandlers(pid: int, func: Callable[[], None]):
    signals = [SIGTERM, SIGABRT, SIGINT]
    handlers = {}
    if 'nt' in osName:
        from signal import SIGBREAK
        signals.append(SIGBREAK)
    elif 'posix' in osName:
        from signal import SIGQUIT, SIGTSTP, SIGHUP, SIGTTIN, SIGTTOU, SIGXCPU
        signals.append(SIGQUIT)
        signals.append(SIGHUP)
        signals.append(SIGXCPU)

        # disallow backgrounding from keyboard, except--obviously--if the terminal implements it as SIGSTOP
        def ignore(s: int, _):
            tprint(f'Ignored signal {Signals(s).name}')

        [signal(x, ignore) for x in [SIGTSTP, SIGTTIN, SIGTTOU]]

    for sig in signals:
        handlers[sig] = getsignal(sig)
        signal(sig, __extendSignalHandlers(pid, handlers, func))
