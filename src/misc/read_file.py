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
from array import array
from io import BufferedReader
from multiprocessing import Value, Queue
from sys import stdin
from typing import Iterable

from numpy import frombuffer, dtype, ndarray, complex128, complex64, ix_, isfinite, invert

from dsp.iq_correction import IQCorrection
from misc.general_util import vprint


def readFile(bitsPerSample: dtype = None,
             dataOffset: int = 0,
             fs: int = None,
             buffers: Iterable[Queue] = None,
             isDead: Value = None,
             inFile: str = None,
             readSize: int = 131072,
             swapEndianness: bool = False,
             correctIq: bool = False,
             normalize: bool = False,
             **_) -> None:
    if fs is None:
        raise ValueError('fs is not specified')

    if swapEndianness:
        bitsPerSample = bitsPerSample.newbyteorder('<' if '>' == bitsPerSample.byteorder else '>')

    dataType = dtype([('re', bitsPerSample), ('im', bitsPerSample)])
    isFile = inFile is not None
    buffer = array(bitsPerSample.char, readSize * b'0')

    def doCorrectIq(_: ndarray[any, dtype[complex64 | complex128]]) -> None:
        pass

    def doNormalize(_: ndarray[any, dtype[complex64 | complex128]]) -> None:
        pass

    if correctIq or (bitsPerSample.char.isupper() and normalize):
        doCorrectIq = IQCorrection(fs).correctIq

    if normalize:
        def doNormalize(Z: ndarray[any, dtype[complex64 | complex128]]) -> None:
            Z[:] = Z / abs(Z)
            ix = invert(isfinite(Z[:, ]))
            Z[ix] = Z[ix_(ix)].all(0)

    def feedBuffers(x: ndarray) -> None:
        x = x['re'] + 1j * x['im']
        doCorrectIq(x)
        doNormalize(x)
        for client in buffers:
            client.put(x)

    with open(inFile if isFile else stdin.fileno(), 'rb', closefd=isFile) as file:
        reader = BufferedReader(file if isFile else stdin.buffer)

        if dataOffset and file.seekable():
            file.seek(dataOffset)
        length = readSize
        while not isDead.value and length == readSize:
            length = reader.readinto(buffer)
            y = frombuffer(buffer, dataType)
            feedBuffers(y)

    for buffer in buffers:
        buffer.put(b'')
        buffer.close()

    vprint('File reader halted')
    return
