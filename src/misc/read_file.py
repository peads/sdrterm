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
import io
import sys
from multiprocessing import Value, Queue
from typing import Iterable

import numpy as np

from misc.general_util import vprint


def readFile(wordtype: np.dtype,
             offset: int,
             buffers: Iterable[Queue] = None,
             isDead: Value = None,
             inFile: str = None,
             readSize: int = 65536,
             swapEndianness: bool = False, **_) -> None:
    if swapEndianness:
        wordtype = wordtype.newbyteorder('<' if '>' == wordtype.byteorder else '>')
    dtype = np.dtype([('re', wordtype), ('im', wordtype)])
    isFile = inFile is not None
    buffer = array.array(wordtype.char, readSize * b'0')

    def feedBuffers(x: np.ndarray) -> None:
        x = x['re'] + 1j * x['im']
        for client in buffers:
            client.put(x)

    with open(inFile if isFile else sys.stdin.fileno(), 'rb', closefd=isFile) as file:
        reader = io.BufferedReader(file if isFile else sys.stdin.buffer)

        if offset and file.seekable():
            file.seek(offset)

        while not isDead.value:
            if not reader.readinto(buffer):
                break
            y = np.frombuffer(buffer, dtype)
            feedBuffers(y)

    for buffer in buffers:
        buffer.put(b'')
        buffer.close()

    vprint('File reader halted')
    return
