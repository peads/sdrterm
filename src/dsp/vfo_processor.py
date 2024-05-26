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
from contextlib import closing
from functools import partial
from multiprocessing import Pool, Pipe, Value
from threading import Barrier

import numpy as np
from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, shiftFreq
from misc.general_util import deinterleave, eprint, printException, initializer, closeSocket
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
        return self.receiver.recv()


class VfoProcessor(DspProcessor):

    def __init__(self,
                 fs: int,
                 centerFreq: float,
                 omegaOut: int,
                 tunedFreq: int,
                 vfos: str,
                 correctIq: bool,
                 decimation: int,
                 **kwargs):
        if not vfos or len(vfos) < 1:
            raise ValueError("simo mode cannot be used without the vfos option")
        super().__init__(fs=fs,
                         centerFreq=centerFreq,
                         omegaOut=omegaOut,
                         tunedFreq=tunedFreq,
                         vfos=vfos,
                         correctIq=correctIq,
                         decimation=decimation, **kwargs)

    def processVfoChunk(self, y, freq) -> np.ndarray[any, np.real] | None:
        try:
            y = shiftFreq(y, freq, self.fs)
            y = signal.decimate(y, self.decimation, ftype='fir')
            y = signal.sosfilt(self.sosIn, y)
            y = self.demod(y)
            return applyFilters(y, self.outputFilters)
        except KeyboardInterrupt:
            return None

    def processData(self, isDead: Value, pipe: Pipe, _) -> None:
        inReader, inWriter = pipe
        outReader, outWriter = outPipe = Pipe(False)
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listenerSckt:
                with PipeReceiver(outPipe, len(self.vfos)) as recvSckt:
                    with Pool(initializer=initializer, initargs=(isDead,)) as pool:

                        server = OutputServer(host='0.0.0.0')
                        lt, ft = server.initServer(recvSckt, listenerSckt, isDead)
                        ft.start()
                        lt.start()

                        eprint(f'\nAccepting connections on port {server.port}\n')
                        while not isDead.value:
                            inWriter.close()
                            y = inReader.recv()
                            if y is None or len(y) < 1:
                                break

                            y = deinterleave(y)
                            if self.correctIq is not None:
                                y = self.correctIq.correctIq(y)
                            y = shiftFreq(y, self.centerFreq, self.fs)

                            results = pool.map_async(partial(self.processVfoChunk, y), self.vfos)
                            [outWriter.send(r) for r in results.get()]
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            pass
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            inReader.close()
            outReader.close()
            outWriter.close()
            closeSocket(listenerSckt)
            print(f'Multi-VFO writer halted')
