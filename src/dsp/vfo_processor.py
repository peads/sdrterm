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
from multiprocessing import Pipe, Value, Queue, JoinableQueue
from threading import Thread

from numpy import pi, array, ndarray, complex128, exp, arange, broadcast_to, ones

from dsp.dsp_processor import DspProcessor
from misc.general_util import eprint, printException, findPort, tprint, vprint, shutdownSocket


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
        self.vfos = array(self.vfos)
        self._nFreq = len(self.vfos)
        self.__omega = -2j * pi * (self.vfos / self.fs)
        self.host = vfoHost
        self.__pipes: dict[str, Pipe] = {k: None for k in self.__omega}
        self.__keys = JoinableQueue()

    def _demod(self, y: ndarray):
        ret = []
        for yy in y:
            ret.append([self.demod(yyy) for yyy in yy])
        return array(ret)

    def _generateShift(self, r: int, c: int) -> None:
        self._shift = ones(shape=(self._nFreq, r, c), dtype=complex128)
        for i, w in enumerate(self.__pipes.keys()):
            shift = exp(w * arange(c))
            self._shift[i][:] = (broadcast_to(shift, (r, c)))
            self.__keys.put(w)
            tprint(f'Put {w}')
        self.__keys.join()
        eprint('Connection(s) established')

    def __processData(self, isDead: Value, buffer: Queue, *args) -> None:
        while not (self._isDead or isDead.value):
            for (pipe, data) in zip(self.__pipes.values(), self._bufferChunk(isDead, buffer)):
                _, w = pipe
                w.send(struct.pack('!' + str(data.size) + 'd', *data.flat))

    def removePipe(self, key):
        try:
            pipe = self.__pipes.pop(key)
            tprint(f'Removing pipe {pipe}')
            r, w = pipe
            r.close()
            w.close()
            tprint(f'Removed pipe {pipe}')
            return True
        except (OSError, ValueError):
            return False

    def removePipes(self):
        for key in list(self.__pipes.keys()):
            self.removePipe(key)

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        children: int = self._nFreq + 1

        class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
            pipes: dict[str, Pipe] = None
            keys: JoinableQueue = None
            outer_self: DspProcessor = self

            def handle(self):
                eprint(f'Connection request from {self.request.getsockname()}')

                r, w = pipe = Pipe(False)
                key = self.keys.get()
                tprint(f'Got {key}')
                self.pipes[key] = pipe
                self.keys.task_done()

                try:
                    while not (self.outer_self._isDead or isDead.value):
                        self.request.sendall(r.recv())
                except (OSError, EOFError) as ex:
                    eprint(f'Client disconnected: {self.request.getsockname()}: {ex}')
                finally:
                    shutdownSocket(self.request)
                    r.close()
                    w.close()
                    del pipe
                    self.request.close()
                    self.keys.put(key)
                    return

        ThreadedTCPRequestHandler.pipes = self.__pipes
        ThreadedTCPRequestHandler.keys = self.__keys
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
                self.__processData(isDead, buffer)
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
                self.removePipes()
                vprint(f'Multi-VFO writer halted')
                return
