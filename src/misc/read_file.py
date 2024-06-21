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

from misc.general_util import eprint, vprint


def __feedBuffers(isDead: Value, data: np.ndarray, buffers: Iterable[Queue], readSize: int):
    i = 0
    while not isDead.value and i < data.shape[0]:
        y = data[i:i + readSize]
        y = y['re'] + 1j * y['im']
        for buffer in buffers:
            buffer.put(y)
        i += readSize


def readFile(wordtype: np.dtype,
             buffers: Iterable[Queue],
             isDead: Value,
             f: str,
             readSize: int = 262144,
             offset: int = 0,
             swapEndianness: bool = False) -> None:
    CHUNK_SIZE = 4096

    if swapEndianness:
         wordtype = wordtype.newbyteorder('<' if '>' == wordtype.byteorder else '>')
    dtype = np.dtype([('re', wordtype), ('im', wordtype)])

    if f is not None:
        data = np.memmap(f, dtype=dtype, mode='r', offset=offset, order='C')
        readSize = (-offset + data.size) // CHUNK_SIZE
        vprint(f'Chunk size: {readSize}')
        __feedBuffers(isDead, data, buffers, readSize)
    else:
        buffer = array.array(wordtype.char, readSize * b'0')
        with open(sys.stdin.fileno(), 'rb', closefd=False) as _:
            file = io.BufferedReader(sys.stdin.buffer)
            while not isDead.value:
                if not file.readinto(buffer):
                    break
                y = np.frombuffer(buffer, dtype)
                __feedBuffers(isDead, y, buffers, readSize)

    for buffer in buffers:
        buffer.put(b'')
        buffer.close()

    eprint('File reader halted')
