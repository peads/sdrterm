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
import os
import socket
from contextlib import closing
from functools import partial
from multiprocessing import Pool, Pipe, Value
from threading import Barrier

import numpy as np
from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, shiftFreq
from misc.general_util import deinterleave, eprint, printException, initializer, closeSocket, applyIgnoreException
from sdr.output_server import OutputServer, Receiver


class PipeReceiver(Receiver):
    def __init__(self, pipe: Pipe, vfos: int):
        receiver, self.__writer = pipe
        super().__init__(receiver, Barrier(vfos + 1))  # +1 for receiver thread

    def __exit__(self, *ex):
        self.__writer.close()
        self._receiver.close()

    def receive(self):
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()
        try:
            return self.receiver.recv()
        except TypeError:
            return b''


class VfoProcessor(DspProcessor):

    def __init__(self,
                 fs: int,
                 centerFreq: float,
                 omegaOut: int,
                 tunedFreq: int,
                 vfos: list[float] | np.ndarray[any, np.real],
                 correctIq: bool,
                 decimation: int,
                 **kwargs):
        if not vfos or len(vfos) < 1:
            raise ValueError("simo mode cannot be used without the vfos option")
        super().__init__(fs=fs,
                         centerFreq=centerFreq,
                         omegaOut=omegaOut,
                         tunedFreq=tunedFreq,
                         vfos=np.array(vfos),
                         correctIq=correctIq,
                         decimation=decimation, **kwargs)

    def processChunk(self, y: list) -> np.ndarray[any, np.real] | None:
        try:
            y = deinterleave(y)
            if self.correctIq is not None:
                y = self.correctIq.correctIq(y)
            y = shiftFreq(y, self.vfos + self.centerFreq, self.fs)
            y = signal.decimate(y, self.decimation, ftype='fir')
            y = signal.sosfilt(self.sosIn, y)
            y = np.array([self.demod(yy) for yy in y])
            return applyFilters(y, self.outputFilters)
        except KeyboardInterrupt:
            return None

    def processData(self, isDead: Value, pipe: Pipe, _) -> None:
        inReader, inWriter = pipe
        outReader, outWriter = outPipe = Pipe(False)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listenerSckt:
            with PipeReceiver(outPipe, len(self.vfos)) as recvSckt:
                with Pool(initializer=initializer, initargs=(isDead,)) as pool:
                    with OutputServer(isDead, host='0.0.0.0') as server:
                        try:
                            lt, ft = server.initServer(recvSckt, listenerSckt, isDead)
                            ft.start()
                            lt.start()

                            eprint(f'\nAccepting connections on port {server.port}\n')
                            ii = range(os.cpu_count())
                            data = []
                            while not isDead.value:
                                for _ in ii:
                                    y = inReader.recv()
                                    if y is None or not len(y):
                                        break
                                    data.append(y)

                                if data is None or not len(data):
                                    outWriter.send(b'')
                                    isDead.value = 1
                                    break
                                y = pool.map_async(self.processChunk, data)
                                for yy in y.get():
                                    for yyy in yy:
                                        outWriter.send(yyy)
                                data.clear()
                        except (EOFError, KeyboardInterrupt, BrokenPipeError, TypeError, OSError):
                            pass
                        except Exception as e:
                            printException(e)
                        finally:
                            isDead.value = 1
                            ft.join(0.1)
                            lt.join(0.1)
                            closeSocket(listenerSckt)
                            applyIgnoreException(
                                partial(outWriter.send, b''),
                                inWriter.close,
                                inReader.close,
                                outReader.close,
                                outWriter.close)
                            print(f'Multi-VFO writer halted')
                            return
