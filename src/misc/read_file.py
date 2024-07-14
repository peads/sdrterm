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
from multiprocessing import Value, Process, Queue

from numpy import dtype
from typing import Iterable


def readFile(bitsPerSample: dtype = None,
             dataOffset: int = 0,
             fs: int = None,
             buffers: Iterable[Queue] = None,
             processes: Iterable[Process] = None,
             isDead: Value = None,
             inFile: str = None,
             readSize: int = 131072,
             swapEndianness: bool = False,
             correctIq: bool = False,
             normalize: bool = False,
             **_) -> None:

    from array import array
    from io import BufferedReader
    from sys import stdin

    from numpy import frombuffer, ndarray, complex128, complex64, ix_, isfinite, invert

    from dsp.iq_correction import IQCorrection
    from misc.general_util import vprint, eprint, tprint, applyIgnoreException

    if fs is None:
        raise ValueError('fs is not specified')

    if swapEndianness:
        bitsPerSample = bitsPerSample.newbyteorder('<' if '>' == bitsPerSample.byteorder else '>')

    dataType = dtype([('re', bitsPerSample), ('im', bitsPerSample)])
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
    procs = list(processes)
    clients = list(buffers)

    def feedBuffers(x: ndarray) -> None:
        x = x['re'] + 1j * x['im']
        doCorrectIq(x)
        doNormalize(x)
        for proc, client in zip(procs, clients):
            if proc.exitcode is not None:
                tprint(f'Process : {proc.name} ended; removing {client} from queue')
                client.close()
                clients.remove(client)
                procs.remove(proc)
            else:
                try:
                    client.put_nowait(x)
                except ValueError:
                    tprint(f'Client : {client} closed; removing {proc.name} from queue')
                    client.close()
                    clients.remove(client)
                    procs.remove(proc)

    def readData(reader: BufferedReader) -> None:
        length = readSize
        while not isDead.value and length == readSize:
            length = reader.readinto(buffer)
            y = frombuffer(buffer, dataType)
            feedBuffers(y)

    def readFd() -> None:
        isFile = inFile is not None
        with open(inFile if isFile else stdin.fileno(), 'rb', closefd=isFile) as file:
            reader = BufferedReader(file if isFile else stdin.buffer)
            if dataOffset and file.seekable():
                file.seek(dataOffset)
            readData(reader)

    def readSocket() -> None:
        from misc.general_util import shutdownSocket
        from socket import socket, AF_INET, SOCK_STREAM, SO_KEEPALIVE, SO_REUSEADDR, SOL_SOCKET, gaierror
        from os import name as osName
        MAX_RETRIES = 5
        retries = 0
        while retries < MAX_RETRIES and not isDead.value:
            try:
                with socket(AF_INET, SOCK_STREAM) as sock:
                    sock.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
                    if 'posix' not in osName:
                        sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                    else:
                        from socket import SO_REUSEPORT
                        sock.setsockopt(SOL_SOCKET, SO_REUSEPORT, 1)
                    sock.settimeout(5)
                    host, port = inFile.split(':')
                    sock.connect((host, int(port)))
                    tprint(f'Connected to {sock.getpeername()}')
                    retries = 0
                    with sock.makefile('rb') as reader:
                        readData(reader)
            except (TimeoutError, ConnectionError, gaierror) as e:
                retries += 1
                eprint(f'Connection failed: {e}. Retrying {retries} of {MAX_RETRIES} times')
            finally:
                shutdownSocket(sock)

    if inFile is not None and ':' in inFile:
        readSocket()
    else:
        readFd()

    for buffer in buffers:
        applyIgnoreException(buffer.put_nowait, b'')
        buffer.close()

    vprint('File reader halted')
    return
