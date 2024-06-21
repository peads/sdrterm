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
import socketserver
import struct
from multiprocessing import Pipe, Value, Queue, Barrier

import numpy as np
from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters
from misc.general_util import eprint, printException
from misc.hooked_thread import HookedThread
from sdr.output_server import findPort


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class VfoProcessor(DspProcessor):

    def __init__(self, host: str = 'localhost', **kwargs):
        super().__init__(**kwargs)
        if self.vfos is None or len(self.vfos) < 1:
            raise ValueError("simo mode cannot be used without the vfos option")
        self.vfos = [float(x) + self.centerFreq for x in self.vfos.split(',') if x is not None]
        self.vfos.append(self.centerFreq)
        self.vfos = np.array(self.vfos)
        self.nFreq = len(self.vfos)
        self.omega = -2j * np.pi * (self.vfos / self.fs)
        self.host = host

    def processData(self, isDead: Value, buffer: Queue, _) -> None:
        children = self.nFreq + 1
        barrier = Barrier(children)
        pipes = []

        class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
            def setup(self):
                eprint(f'Connection request from {self.request.getsockname()}')
                if not barrier.broken:
                    barrier.wait()

            def handle(self):
                r, w = pipe = Pipe(False)
                pipes.append(pipe)
                while not isDead.value:
                    try:
                        self.request.sendall(r.recv())
                    except (EOFError, ConnectionError):
                        eprint(f'Client disconnected: {self.request.getsockname()}')
                        pipes.remove(pipe)
                        r.close()
                        w.close()
                        return

        def shift(Y: np.ndarray, n: int) -> np.ndarray:
            t = np.arange(n)
            s = np.exp([w * t for w in self.omega])
            ret = Y * s
            return ret

        with ThreadedTCPServer((self.host, findPort()), ThreadedTCPRequestHandler) as server:
            server.max_children = children
            thread = HookedThread(isDead, target=server.serve_forever, daemon=True)
            thread.start()

            try:
                eprint(f'\nAccepting connections on port {server.socket.getsockname()[1]}\n')
                if not barrier.broken:
                    barrier.wait()

                while not isDead.value:
                    y = buffer.get()
                    length = len(y)
                    if y is None or not length:
                        isDead.value = 1
                        break

                    if self.correctIq is not None:
                        y = self.correctIq.correctIq(y)
                    y = np.broadcast_to(y, (self.nFreq, length))
                    y = shift(y, length)
                    if self._decimationFactor > 1:
                        y = signal.decimate(y, self.decimation, ftype='fir')
                    y = signal.sosfilt(self.sosIn, y)
                    y = [self.demod(yy) for yy in y]
                    y = applyFilters(y, self.outputFilters)
                    for (pipe, data) in zip(pipes, y):
                        r, w = pipe
                        try:
                            w.send(struct.pack('!' + (len(data) * 'd'), *data))
                        except ConnectionError:
                            pipes.remove(pipe)
                            r.close()
                            w.close()
                    barrier.abort()
            except (EOFError, KeyboardInterrupt, ConnectionError, TypeError):
                pass
            except Exception as e:
                printException(e)
            finally:
                buffer.close()
                buffer.cancel_join_thread()
                thread.join(5)
                eprint(f'Multi-VFO writer halted')
                return
