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
from io import RawIOBase
from multiprocessing import Value
from os import name as osName
from socket import socket, AF_INET, SOCK_STREAM, SO_KEEPALIVE, SO_REUSEADDR, SOL_SOCKET, gaierror
from threading import Lock, Event
from typing import Iterable

from numpy import log2

from misc.general_util import shutdownSocket, eprint, findMtu
from sdr.receiver import Receiver


class SocketReceiver(Receiver):
    _BUF_SIZE = 8192
    _MAX_RETRIES = 5

    def __init__(self, isDead: Value, host: str = None, port: int = None):
        self._clients: dict[RawIOBase, Event] = {}
        self.host = host
        self.port = port
        self.__cond = Lock()
        super().__init__()
        self.isDead = isDead
        self.__buffer: array = array('B', self._BUF_SIZE * b'\0')

    def __exit__(self, *ex):
        self.disconnect()
        self._removeClients()
        self.__cond = None
        self._receiver = None

    def disconnect(self):
        if self._receiver is not None:
            shutdownSocket(self._receiver)
            self._receiver.close()

    def reset(self) -> None:
        size = self._BUF_SIZE
        mtu = findMtu(self._receiver)
        if mtu > len(self.__buffer):
            size = 1 << int(log2(mtu))
            eprint(f'Re-sizing buffer from {len(self.__buffer)} to {size}')
        with self.__cond:
            self.__buffer: array = array('B', size * b'\0')

    def _connect(self):
        self._receiver.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
        if 'posix' not in osName:
            self._receiver.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        else:
            from socket import SO_REUSEPORT
            self._receiver.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
        self._receiver.settimeout(5)
        self._receiver.connect((self.host, self.port))
        self.reset()

    def __receive(self, clients: Iterable[RawIOBase]) -> None:
        for client in clients:
            try:
                client.write(self.__buffer)
            except (ConnectionError, EOFError, ValueError):
                self._removeClient(client)

    def _receive(self, file) -> int:
        while not self.isDead.value:
            with self.__cond:
                if not file.readinto(self.__buffer):
                    break
                clients = list(self._clients.keys())
            self.__receive(clients)
        return self._MAX_RETRIES

    def receive(self) -> None:
        retries = 0
        while retries < self._MAX_RETRIES and not self.isDead.value:
            with socket(AF_INET, SOCK_STREAM) as self._receiver:
                try:
                    self._connect()
                    retries = 0
                    with self._receiver.makefile('rb') as file:
                        retries = self._receive(file)
                except (TimeoutError, ConnectionError, gaierror) as e:
                    self.disconnect()
                    retries += 1
                    eprint(f'Connection failed: {e}. Retrying {retries} of {self._MAX_RETRIES} times')
        return

    def _removeClients(self):
        if self.__cond is not None:
            for client in list(self._clients.keys()):
                self._removeClient(client)

    def addClient(self, request: RawIOBase) -> Event:
        event = Event()
        with self.__cond:
            self._clients[request] = event
        return event

    def _removeClient(self, request: RawIOBase):
        with self.__cond:
            event = self._clients.pop(request)
        event.set()
