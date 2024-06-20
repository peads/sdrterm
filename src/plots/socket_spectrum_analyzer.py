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
import socket
import struct

from misc.general_util import shutdownSocket, deinterleave
from plots.spectrum_analyzer import SpectrumAnalyzer


class SocketSpectrumAnalyzer(SpectrumAnalyzer):

    def __init__(self, sock: socket.socket, readSize: int = 4096, structtype: str = 'B', **kwargs):
        super().__init__(**kwargs)
        self.sock = sock
        self.readSize = readSize
        self.structtype = structtype
        self.bitdepth = struct.calcsize(structtype) - 1  # int(np.log2(struct.calcsize(structtype) << 3) - 2)

    def __del__(self):
        shutdownSocket(self.sock)
        self.sock.close()

    def receiveData(self):
        data = self.sock.recv(self.readSize)
        data = struct.unpack('!' + ((len(data) >> self.bitdepth) * self.structtype), data)
        return deinterleave(data)
