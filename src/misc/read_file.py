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
import struct
import sys
from multiprocessing import Value
from typing import Iterable

from misc.general_util import eprint


def readFile(wordtype, buffers: Iterable, isDead: Value, f: str, readSize: int = 65536, offset: int = 0) -> None:

    bitdepth, structtype = wordtype

    with open(f, 'rb') if f is not None else open(sys.stdin.fileno(), 'rb', closefd=False) as file:
        if offset:
            file.seek(offset)  # skip the wav header(s)

        while not isDead.value:
            data = file.read(readSize)
            y = struct.unpack('!' + (len(data) >> bitdepth) * structtype, data)

            for buffer in buffers:
                buffer.put(y)

    for buffer in buffers:
        buffer.close()

    eprint('File reader halted')
