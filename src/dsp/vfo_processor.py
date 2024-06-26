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
from misc.general_util import eprint, printException, findPort, tprint
from misc.keyboard_interruptable_thread import KeyboardInterruptableThread


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
                _, w = pipe
                w.send(struct.pack('!' + str(data.size) + 'd', *data.flat))
        for pipe in pipes:
            VfoProcessor.removePipe(pipes, pipe)

    @staticmethod
    def removePipe(pipes, pipe):
        try:
            eprint(f'Removing pipe {pipe}')
            pipes.remove(pipe)
            r, w = pipe
            r.close()
            w.close()
            eprint(f'Removed pipe {pipe}')
            return True
        except (OSError, ValueError):
            return False

    @staticmethod
    def removePipes(pipes):
        for pipe in list(pipes):
            VfoProcessor.removePipe(pipes, pipe)

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        children: int = self.nFreq + 1
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
            def setup(self):
                eprint(f'Connection request from {self.request.getsockname()}')
                awaitBarrier()

            def handle(self):
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
            def handleExceptionHook():
                isDead.value = 1
                barrier.abort()
                self.removePipes(pipes)
                buffer.close()
                buffer.cancel_join_thread()

            server.max_children = children
            thread = KeyboardInterruptableThread(handleExceptionHook, target=server.serve_forever, daemon=True)
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
                handleExceptionHook()
                tprint(f'{type(server).__name__} shutting down')
                server.shutdown()
                server.server_close()
                tprint(f'{type(server).__name__} shutdown')
                tprint(f'{type(buffer).__name__} shutting down')
                buffer.close()
                buffer.join_thread()
                tprint(f'{type(buffer).__name__} shut down')
                tprint(f'Awaiting {thread}')
                thread.join(5)
                tprint(f'{thread} joined')
                eprint(f'Multi-VFO writer halted')
                return
