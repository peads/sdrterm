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
from misc.general_util import shutdownSocket
from sdr.output_server import Receiver


class SocketReceiver(Receiver):

    def __init__(self, writeSize=262144, readSize=8192):
        super().__init__()  # socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.readSize = readSize
        self.data = bytearray()
        self.chunks = range(writeSize // readSize)
        self._writeSize = writeSize

    def __exit__(self, *ex):
        shutdownSocket(self._receiver)

    @property
    def writeSize(self):
        return self._writeSize

    @writeSize.setter
    def writeSize(self, _):
        raise NotImplementedError('WriteSize is immutable')

    @writeSize.deleter
    def writeSize(self):
        del self._writeSize

    def receive(self):
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()
        for _ in self.chunks:
            try:
                inp = self.receiver.recv(self.readSize)
            except BrokenPipeError:
                return b''
            if inp is None or not len(inp):
                break
            self.data.extend(inp)
        result = bytes(self.data)
        self.data.clear()
        return result
