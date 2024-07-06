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
from array import array
from multiprocessing import Value
from os import name as osName
from socket import socket, AF_INET, SOCK_STREAM, SO_KEEPALIVE, SO_REUSEADDR, SOL_SOCKET
from threading import Lock
from typing import Generator

from misc.general_util import shutdownSocket
from sdr.receiver import Receiver


class SocketReceiver(Receiver):
    BUF_SIZE = 8192

    def __init__(self, isDead: Value, host: str = None, port: int = None):
        self.isDisconnected = False
        self.host = host
        self.port = port
        self.__cond = Lock()
        super().__init__()
        self.isDead = isDead
        self.__buffer: array | None = None

    def __exit__(self, *ex):
        self.disconnect()

    def disconnect(self):
        self.isDisconnected = True
        if self._receiver is not None:
            shutdownSocket(self._receiver)
            self._receiver.close()
        self.__cond = None

    def connect(self):
        self.reset()
        self.isDisconnected = not (self.host is None or self.port is None)

    def reset(self, size: int = BUF_SIZE) -> None:
        with self.__cond:
            self.__buffer: array = array('B', size * b'\0')

    def receive(self) -> Generator:
        while not self.isDead.value:
            with socket(AF_INET, SOCK_STREAM) as self._receiver:
                try:
                    self._receiver.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
                    if 'posix' not in osName:
                        self._receiver.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                    else:
                        from socket import SO_REUSEPORT
                        self._receiver.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
                    self._receiver.settimeout(5)
                    self._receiver.connect((self.host, self.port))
                    self.isDisconnected = False

                    with self._receiver.makefile('rb') as file:
                        while not (self.isDisconnected or self.isDead.value):
                            with self.__cond:
                                if not file.readinto(self.__buffer):
                                    break
                                yield self.__buffer[:]
                finally:
                    yield b''
        return None
