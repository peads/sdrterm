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
from threading import BrokenBarrierError

import numpy as np

from dsp.dsp_processor import DspProcessor
from misc.general_util import eprint, printException, findPort
from misc.hooked_thread import HookedThread


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class VfoProcessor(DspProcessor):

    def __init__(self, fs, vfoHost: str = 'localhost', vfos: str = None, **kwargs):
        super().__init__(fs, **kwargs)
        if vfos is None or len(vfos) < 1:
            raise ValueError("simo mode cannot be used without the vfos option")
        self.vfos = vfos.split(',')
        self.vfos = [int(x) + self.centerFreq for x in self.vfos if x is not None]
        self.vfos.append(self.centerFreq)
        self.vfos = np.array(self.vfos)
        self.nFreq = len(self.vfos)
        self.omega = -2j * np.pi * (self.vfos / self.fs)
        self.host = vfoHost

    def _demod(self, y: np.ndarray):
        ret = []
        for yy in y:
            ret.append([self.demod(yyy) for yyy in yy])
        return np.array(ret)

    def _generateShift(self, r: int, c: int) -> np.ndarray | None:
        if not self.centerFreq:
            return None
        else:
            ret = []
            shifts = np.exp([w * np.arange(c) for w in self.omega])
            for shift in shifts:
                ret.append(np.broadcast_to(shift, (r, c)))
            return np.array(ret)

    def __processData(self, isDead: Value, buffer: Queue, pipes: list[Pipe]) -> None:
        Y = None
        shift = None
        while not isDead.value:
            Y, shift, y = self._bufferChunk(isDead, buffer, Y, shift)

            for (pipe, data) in zip(pipes, y):
                r, w = pipe
                try:
                    w.send(struct.pack('!' + str(data.size) + 'd', *data.flat))
                except (ConnectionError, EOFError):
                    pipes.remove(pipe)
                    r.close()
                    w.close()
        for pipe in pipes:
            r, w = pipe
            pipes.remove(pipe)
            r.close()
            w.close()

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        children = self.nFreq + 1
        barrier = Barrier(children)
        pipes = []

        def awaitBarrier():
            try:
                if not barrier.broken:
                    barrier.wait()
                    barrier.abort()
            except BrokenBarrierError:
                pass

        class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
            def setup(self):
                eprint(f'Connection request from {self.request.getsockname()}')
                awaitBarrier()

            def handle(self):
                r, w = pipe = Pipe(False)
                pipes.append(pipe)
                while not isDead.value:
                    try:
                        self.request.sendall(r.recv())
                    except (ConnectionError, EOFError) as ex:
                        eprint(f'Client disconnected: {self.request.getsockname()}: {ex}')
                        pipes.remove(pipe)
                        r.close()
                        w.close()
                        return

        with ThreadedTCPServer((self.host, findPort()), ThreadedTCPRequestHandler) as server:
            server.max_children = children
            thread = HookedThread(isDead, target=server.serve_forever, daemon=True)
            thread.start()

            try:
                eprint(f'\nAccepting connections on {server.socket.getsockname()}\n')
                awaitBarrier()
                eprint('Connection(s) established')
                self.__processData(isDead, buffer, pipes)
            except (KeyboardInterrupt, TypeError):
                pass
            except Exception as e:
                printException(e)
            finally:
                barrier.abort()
                buffer.close()
                buffer.cancel_join_thread()
                server.shutdown()
                thread.join(5)
                eprint(f'Multi-VFO writer halted')
                return
