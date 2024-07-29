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
from io import BufferedReader
from multiprocessing import Value, Process, Queue
from sys import stdin
from typing import Iterable

from numba import njit
from numpy import frombuffer, ndarray, complexfloating, dtype, empty, uint8

from misc.general_util import vprint, eprint, tprint, applyIgnoreException


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
             isSocket: bool = False,
             **_) -> None:
    if fs is None:
        raise ValueError('fs is not specified')

    if swapEndianness:
        bitsPerSample = bitsPerSample.newbyteorder('<' if '>' == bitsPerSample.byteorder else '>')

    dataType = dtype([('re', bitsPerSample), ('im', bitsPerSample)])
    buffer = empty(readSize, dtype=uint8)

    def _correctIq(_: ndarray[any, dtype[complexfloating]]) -> None:
        pass

    if correctIq:
        try:
            from dsp.fast.iq_correction import IQCorrection
            tprint('Imported pre-compiled IQCorrection class')
        except ImportError:
            from dsp.iq_correction import IQCorrection
            tprint('Falling-back to jit IQCorrection class')
        _correctIq = IQCorrection(fs).correctIq

    def noNormalize(*_) -> None:
        pass

    if not normalize:
        _normalize = noNormalize
    else:
        ret = generateDomain(bitsPerSample.char)
        if ret is None:
            _normalize = noNormalize
        else:
            xmin, xMaxMinDiff = ret

            @njit(cache=True, nogil=True, error_model='numpy', boundscheck=False, fastmath=True)
            def _normalize(z: ndarray[any, dtype[complexfloating]]) -> None:
                for i in range(z.shape[0]):
                    z[i] = 1.6 * (z[i] - xmin) * xMaxMinDiff - 0.8
    procs = list(processes)
    clients = list(buffers)

    def feedBuffers(y: ndarray) -> None:
        z = y['re'] + 1j * y['im']
        _normalize(z)
        _correctIq(z)
        for proc, client in zip(procs, clients):
            if proc.exitcode is not None:
                tprint(f'Process : {proc.name} ended; removing {client} from queue')
                client.close()
                clients.remove(client)
                procs.remove(proc)
            else:
                try:
                    client.put_nowait(z)
                except ValueError:
                    tprint(f'Client : {client} closed; removing {proc.name} from queue')
                    client.close()
                    clients.remove(client)
                    procs.remove(proc)

    def readData(reader: BufferedReader) -> None:

        while not isDead.value:
            if not reader.readinto(buffer):
                break
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
        from socket import socket, AF_INET, SOCK_STREAM, SO_KEEPALIVE, SO_REUSEADDR, SOL_SOCKET, \
            gaierror
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

    if isSocket:
        readSocket()
    else:
        readFd()

    for buffer in buffers:
        applyIgnoreException(buffer.put_nowait, b'')
        buffer.close()

    vprint('File reader halted')
    return


def generateDomain(dataType: str) -> tuple[int, float] | None:
    if 'B' == dataType:
        xmin, xmax = 0, 255
    elif 'h' == dataType:
        xmin, xmax = -32768, 32767
    elif 'b' == dataType:
        xmin, xmax = -128, 127
    elif 'i' == dataType:
        xmin, xmax = -2147483648, 2147483647
    elif 'H' == dataType:
        xmin, xmax = 0, 65536
    elif 'I' == dataType:
        xmin, xmax = 0, 4294967295
    elif 'L' == dataType:
        xmin, xmax = 0, 18446744073709551615
    elif 'l' == dataType:
        xmin, xmax = -9223372036854775808, 9223372036854775807
    else:
        return None
    return xmin, 1 / (-xmin + xmax)
