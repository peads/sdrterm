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
import socket
from multiprocessing import Value

import numpy as np

from misc.general_util import shutdownSocket, vprint
from sdr.receiver import Receiver


class SocketReceiver(Receiver):
    BUF_SIZE = 262144

    def __init__(self, isDead: Value, readSize: int = 4096):
        super().__init__()
        self.isDead = isDead
        if readSize < 32:  # minimum is the size in bytes of four doubles representing two 128-bit complex numbers
            self.readSize = 32
        else:
            self.readSize = 1 << int(np.round(np.log2(readSize)))
        vprint(f'Requested read size: {readSize}\nRead size: {self.readSize}')
        self.data = bytearray()

    def __exit__(self, *ex):
        shutdownSocket(self._receiver)

    @property
    def receiver(self):
        return self._receiver

    @receiver.setter
    def receiver(self, _):
        if self._receiver is not None:
            self._receiver.close()
        self._receiver = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._receiver.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._receiver.settimeout(2)

    @receiver.deleter
    def receiver(self):
        del self._receiver

    def receive(self):
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()

        try:
            length = len(self.data)
            while not self.isDead.value:
                readSize = -length + self.BUF_SIZE
                readSize = readSize if readSize < self.readSize else self.readSize
                if readSize < 1:
                    break
                temp = self.receiver.recv(readSize)
                if temp is None or not len(temp):
                    break
                self.data += temp
                length = len(self.data)
            if length != self.BUF_SIZE:
                vprint(f'Receive unexpected number of bytes: {"overrun" if length > self.BUF_SIZE else "underrun"}')
            ret = bytes(self.data)
            self.data.clear()

            return ret
        except (ValueError, ConnectionError, EOFError):
            return b''
