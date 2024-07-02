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
from os import name as osName
from array import array
from multiprocessing import Value
from socket import socket, AF_INET, SOCK_STREAM, SO_KEEPALIVE, SO_REUSEPORT, SO_REUSEADDR, SOL_SOCKET
from threading import Lock
from typing import Generator

from misc.general_util import shutdownSocket, tprint
from sdr.receiver import Receiver


class SocketReceiver(Receiver):
    BUF_SIZE = 65536  # 262144

    def __init__(self, isDead: Value, host: str = None, port: int = None):
        self.host = host
        self.port = port
        self.__cond = Lock()
        super().__init__()
        self.isDead = isDead
        self.__buffer = array('B', self.BUF_SIZE * b'0')

    def __exit__(self, *ex):
        self.__cond = None
        self.disconnect()

    def disconnect(self):
        if self._receiver is not None:
            shutdownSocket(self._receiver)
            self._receiver.close()
        self.barrier.abort()

    def connect(self):
        if self.host is None or self.port is None:
            tprint('Warning: Socket cannot be connected without both  host and port specified')
        else:
            with self.__cond:
                self._receiver = socket(AF_INET, SOCK_STREAM)
                self._receiver.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
                self._receiver.setsockopt(SOL_SOCKET, SO_REUSEPORT if 'posix' in osName else SO_REUSEADDR, 1)
                self._receiver.settimeout(5)
                self._receiver.connect((self.host, self.port))

    def reset(self, fs: int) -> None:
        with self.__cond:
            from numpy import log2 as nplog2
            size = self.BUF_SIZE if fs > self.BUF_SIZE else (1 << int(nplog2(fs)))
            tprint(f'Resetting buffers: {size}')
            self.__buffer = array('B', size * b'0')
            tprint('Buffers reset')

    def receive(self) -> Generator:
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()

        if self._receiver is not None:
            file = self._receiver.makefile('rb')
            try:
                while not self.isDead.value:
                    with self.__cond:
                        if not file.readinto(self.__buffer):
                            break
                        yield self.__buffer[:]
            finally:
                file.close()
                return None
