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
from threading import BrokenBarrierError, Thread

import numpy as np

from dsp.dsp_processor import DspProcessor
from misc.general_util import eprint, printException, findPort, tprint, vprint


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class VfoProcessor(DspProcessor):

    def __init__(self, fs, vfoHost: str = 'localhost', vfos: str = None, **kwargs):
        super().__init__(fs, **kwargs)
        if vfos is None or len(vfos) < 1:
            raise ValueError('simo mode cannot be used without the vfos option')
        self.vfosStr = vfos + ',0'
        self.vfos = vfos.split(',')
        self.vfos = [int(x) + self.centerFreq for x in self.vfos if x is not None]
        self.vfos.append(self.centerFreq)
        self.vfos = np.array(self.vfos)
        self._nFreq = len(self.vfos)
        self.omega = -2j * np.pi * (self.vfos / self.fs)
        self.host = vfoHost

    def _demod(self, y: np.ndarray):
        ret = []
        for yy in y:
            ret.append([self.demod(yyy) for yyy in yy])
        return np.array(ret)

    def _generateShift(self, r: int, c: int) -> None:
        self._shift = np.ones(shape=(self._nFreq, r, c), dtype=np.complex128)
        if self.centerFreq:
            shifts = np.exp([w * np.arange(c) for w in self.omega])
            for i, shift in enumerate(shifts):
                self._shift[i][:] = (np.broadcast_to(shift, (r, c)))

    def __processData(self, isDead: Value, buffer: Queue, pipes: list[Pipe]) -> None:

        while not isDead.value:
            y = self._bufferChunk(isDead, buffer)

            for (pipe, data) in zip(pipes, y):
                _, w = pipe
                w.send(struct.pack('!' + str(data.size) + 'd', *data.flat))
        for pipe in pipes:
            VfoProcessor.removePipe(pipes, pipe)

    @staticmethod
    def removePipe(pipes, pipe):
        try:
            tprint(f'Removing pipe {pipe}')
            pipes.remove(pipe)
            r, w = pipe
            r.close()
            w.close()
            tprint(f'Removed pipe {pipe}')
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def removePipes(pipes):
        for pipe in list(pipes):
            VfoProcessor.removePipe(pipes, pipe)

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        children: int = self._nFreq + 1
        barrier: Barrier = Barrier(children)
        pipes: list[Pipe] = []

        def awaitBarrier():
            try:
                if not barrier.broken:
                    barrier.wait()
                    barrier.abort()
            except BrokenBarrierError:
                pass

        class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
            def handle(self):
                eprint(f'Connection request from {self.request.getsockname()}')
                awaitBarrier()
                r, w = pipe = Pipe(False)
                pipes.append(pipe)
                while not isDead.value:
                    try:
                        self.request.sendall(r.recv())
                    except (OSError, EOFError) as ex:
                        eprint(f'Client disconnected: {self.request.getsockname()}: {ex}')
                        VfoProcessor.removePipe(pipes, pipe)
                        del pipe
                        self.request.close()
                        return
                VfoProcessor.removePipe(pipes, pipe)
                del pipe
                self.request.close()
                return

        with ThreadedTCPServer((self.host, findPort()), ThreadedTCPRequestHandler) as server:
            server.max_children = children
            thread = Thread(target=server.serve_forever)
            thread.start()
            isShutdown = False
            def shutdown():
                if not isShutdown:
                    serverName = server.__class__.__name__
                    tprint(f'{buffer} shutting down')
                    buffer.close()
                    buffer.join_thread()
                    tprint(f'{buffer} shut down')
                    tprint(f'{serverName} shutting down')
                    server.shutdown()
                    tprint(f'{serverName} shutdown')
                    return True
                return isShutdown

            try:
                eprint(f'\nAccepting connections on {server.socket.getsockname()}\n')
                awaitBarrier()
                eprint('Connection(s) established')
                self.__processData(isDead, buffer, pipes)
                isShutdown = shutdown()
                threadName = thread.__class__.__name__
                tprint(f'Awaiting {threadName}')
                thread.join()
                tprint(f'{threadName} joined')
            except (KeyboardInterrupt, TypeError):
                pass
            except Exception as e:
                printException(e)
            finally:
                isShutdown = shutdown()
                thread.join(5)
                self.removePipes(pipes)
                vprint(f'Multi-VFO writer halted')
                return
