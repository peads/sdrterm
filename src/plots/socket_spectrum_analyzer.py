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
import array
import socket
import struct

import numpy as np

from plots.spectrum_analyzer import SpectrumAnalyzer


class SocketSpectrumAnalyzer(SpectrumAnalyzer):

    def __init__(self, sock: socket.socket, readSize: int = 4096, structtype: str = 'B', **kwargs):
        super().__init__(**kwargs)
        self.sock = sock
        self.readSize = readSize
        self.structtype = structtype
        self.bitdepth = struct.calcsize(structtype) - 1  # int(np.log2(struct.calcsize(structtype) << 3) - 2)
        dt = '>' + structtype
        self.dtype = np.dtype([('re', dt), ('im', dt)])
        self.buffer = array.array('B', b'0' * readSize)

    def receiveData(self):
        self.sock.recv_into(self.buffer, self.readSize)
        data = np.frombuffer(self.buffer, self.dtype)
        self.length = len(self.buffer)
        return data['re'] + 1j * data['im']
