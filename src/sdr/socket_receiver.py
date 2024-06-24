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
import array
import socket
from multiprocessing import Value
from threading import Condition
from typing import Generator

from misc.general_util import shutdownSocket, eprint, printException, vprint
from sdr.receiver import Receiver


class SocketReceiver(Receiver):
    BUF_SIZE = 262144

    def __init__(self, isDead: Value, host: str = None, port: int = None):
        self.host = host
        self.port = port
        self.__cond = Condition()
        self.__isConnected = False
        super().__init__()
        self.isDead = isDead
        self.__buffer = array.array('B', self.BUF_SIZE * b'0')

    def __exit__(self, *ex):
        self.disconnect()

    def disconnect(self):
        if self._receiver is not None:
            shutdownSocket(self._receiver)
            self._receiver.close()

        if not self.barrier.broken:
            self.barrier.abort()

        if self.__cond is not None:
            with self.__cond:
                self.__cond.notify_all()
        self.__isConnected = False

    def connect(self):
        if not (self.host is None or self.port is None):
            self._receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._receiver.settimeout(1)
            self._receiver.connect((self.host, self.port))
            with self.__cond:
                self.__cond.notify()
            self.__isConnected = True

    def awaitConnection(self):
        if not self.__isConnected:
            with self.__cond:
                eprint('Awaiting connection')
                self.__cond.wait()
                eprint('Connection established')
        return self.__isConnected

    def reset(self, size: int = None):
        vprint(f'Resetting buffers: {size}')
        self.__isConnected = False
        with self.__cond:
            self.__buffer = array.array('B', (size if size is not None and size != self.BUF_SIZE else self.BUF_SIZE) * b'0')
            self.__cond.notify()
        self.__isConnected = True


    def receive(self) -> Generator:
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()

        if self._receiver is not None:
            file = self._receiver.makefile('rb')
            try:
                while not self.isDead.value and self.awaitConnection():
                    if not file.readinto(self.__buffer):
                        break
                    yield self.__buffer[:]
            finally:
                file.close()
                return None
