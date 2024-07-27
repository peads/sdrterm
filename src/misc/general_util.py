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
from os import name as osName, getpid
from signal import SIGTERM, Signals, signal, SIGINT
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR, SHUT_RDWR
from sys import stderr
from types import FrameType
from typing import Callable, TextIO, Iterable


class __VerbosePrint:
    vlog = lambda *_, **__: None
    tlog = lambda *_, **__: None

    @classmethod
    def vprint(cls, *args, **kwargs) -> None:
        cls.vlog(*args, **kwargs)

    @classmethod
    def tprint(cls, *args, **kwargs) -> None:
        cls.tlog(*args, **kwargs)


def eprint(*args,
           func: Callable[[any, TextIO, any], None] = lambda *a, **k: print(*a, file=stderr, **k),
           **kwargs) -> None:
    func(*args, **kwargs)


def vprint(*args, **kwargs) -> None:
    __VerbosePrint.vprint(*args, **kwargs)


def tprint(*args, **kwargs) -> None:
    __VerbosePrint.tprint(*args, **kwargs)


def printException(*args, **kwargs) -> None:
    from traceback import print_exc
    from multiprocessing import current_process
    eprint(f'Process {current_process().name} raised exception:', *args, **kwargs)
    print_exc(file=stderr)


def applyIgnoreException(func: Callable[[any], any], *args) -> any:
    try:
        return func(*args)
    except Exception as e:
        return e


def __multiApplyIgnoreException(*func: Callable[[any], any], args: Iterable[tuple[any]] = None) -> \
list[any]:
    ret = []
    for f, arg in zip(func, args):
        ret.append(applyIgnoreException(f, *arg))
    return ret


def verboseOn() -> None:
    __VerbosePrint.vlog = eprint


def traceOn() -> None:
    verboseOn()
    __VerbosePrint.tlog = eprint


def shutdownSocket(*socks: socket) -> None:
    for sock in socks:
        __multiApplyIgnoreException(sock.send, sock.shutdown, args=((b'',), (SHUT_RDWR,)))


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost') -> int:
    with closing(socket(AF_INET, SOCK_STREAM)) as s:
        if 'posix' not in osName:
            s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        else:
            from socket import SO_REUSEPORT
            s.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        s.bind((host, 0))
        return s.getsockname()[1]


def findMtu(sock: socket) -> int:
    from psutil import net_if_stats, net_if_addrs
    filtered_stats = {k: v.mtu for k, v in net_if_stats().items()}
    if '0.0.0.0' == sock.getsockname()[0]:
        return min(filtered_stats.values())
    else:
        filtered_addrs = {k: x.address for k, v in net_if_addrs().items() for x in v if
                          x.address == sock.getsockname()[0]}
        return min((filtered_stats[k] for k in filtered_addrs.keys()))


def killChildren(_, sig):
    from psutil import Process, NoSuchProcess
    parent = Process(getpid())
    children = parent.children(recursive=True)
    for child in children:
        try:
            tprint(f'Re-throwing {Signals(sig).name} to pid: {child.pid}')
            child.send_signal(sig)
        except NoSuchProcess:
            pass


def __extendSignalHandlers(pid: int, sigs: tuple, handlePostSignal: Callable[[], None]) \
        -> Callable[[int, FrameType | None], None]:
    def handleSignal(sig: int, frame: FrameType) -> None:
        tprint(f'Frame: {frame}')
        eprint(f'pid {pid} caught: {Signals(sig).name}')
        handlePostSignal()
        tprint(f'Handlers after processing: {[signal(s, killChildren) for s in sigs]}')

    return handleSignal


def setSignalHandlers(pid: int, func: Callable[[], None]):
    signals = [SIGTERM, SIGINT]
    if 'nt' in osName:
        from signal import SIGBREAK
        signals.append(SIGBREAK)
    elif 'posix' in osName:
        from signal import SIGABRT, SIGQUIT, SIGTSTP, SIGHUP, SIGTTIN, SIGTTOU, SIGXCPU
        signals.extend([SIGQUIT, SIGABRT, SIGHUP, SIGXCPU])

        # disallow backgrounding from keyboard, except--obviously--if the terminal implements it as SIGSTOP
        def ignore(s: int, _):
            vprint(f'Ignored signal {Signals(s).name}')

        [signal(x, ignore) for x in (SIGTSTP, SIGTTIN, SIGTTOU)]

    for sig in signals:
        signal(sig, __extendSignalHandlers(pid, tuple(signals), func))
