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


def readFile(wordtype,
             buffers: Iterable[Queue],
             isDead: Value,
             f: str,
             readSize: int = 262144,
             offset: int = 0,
             swapEndianness: bool = False) -> None:
    CHUNK_SIZE = 4096
    bitdepth, structtype = wordtype
    dt = ('>' if not swapEndianness else '<') + structtype
    dtype = np.dtype([('re', dt), ('im', dt)])
    if f is not None:
        data = np.memmap(f, dtype=dtype, mode='r', offset=offset, order='C')
        readSize = (-offset + data.size) // CHUNK_SIZE
        vprint(f'Chunk size: {readSize}')
        __feedBuffers(isDead, data, buffers, readSize)
    else:
        with open(sys.stdin.fileno(), 'rb', closefd=False) as file:
            if offset:
                file.seek(offset)  # skip the wav header(s)

            while not isDead.value:
                data = file.read(readSize)
                y = np.frombuffer(data, dtype)
                __feedBuffers(isDead, y, buffers, 4096)

    for buffer in buffers:
        buffer.put(b'')
        buffer.close()

    eprint('File reader halted')
