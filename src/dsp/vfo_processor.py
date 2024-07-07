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
from io import RawIOBase
from multiprocessing import Value
from queue import Queue
from threading import Thread, Event

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

        self.__queue: Queue[str] | None = None
        self.__clients: dict[str, RawIOBase] | None = None
        self.__event: Event | None = None

    @property
    def clients(self) -> dict[str, RawIOBase]:
        return self.__clients

    @clients.setter
    def clients(self, _):
        raise NotImplemented('Setting queue is not allowed')

    @clients.deleter
    def clients(self):
        del self.__clients

    @property
    def event(self) -> Event:
        return self.__event

    @event.setter
    def event(self, _):
        raise NotImplemented('Setting queue is not allowed')

    @event.deleter
    def event(self):
        del self.__event

    @property
    def queue(self) -> Queue[str]:
        return self.__queue

    @queue.setter
    def queue(self, _):
        raise NotImplemented('Setting queue is not allowed')

    @queue.deleter
    def queue(self):
        del self.__queue

    def _demod(self, y: ndarray):
        ret = []
        for yy in y:
            ret.append([self.demod(yyy) for yyy in yy])
        return array(ret)

    def _generateShift(self, r: int, c: int) -> None:
        self._shift = ones(shape=(self._nFreq, r, c), dtype=complex128)
        for i, w in enumerate(self.__omega):
            shift = exp(w * arange(c))
            self._shift[i][:] = (broadcast_to(shift, (r, c)))
            self.queue.put(w)
            tprint(f'Put {w}')
        self.queue.join()
        eprint('Connection(s) established')

    def __processData(self, isDead: Value, buffer: Queue, *args) -> None:
        while not (self._isDead or isDead.value):
            for (request, data) in zip(self.__clients.values(), self._bufferChunk(isDead, buffer)):
                request.write(struct.pack('!' + str(data.size) + 'd', *data.flat))

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        self.__queue = Queue()
        self.__event = Event()
        self.__clients = {}

        class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
            outer_self: VfoProcessor = self

            def finish(self):
                eprint(f'Client disconnected: {self.request.getsockname()}')
                shutdownSocket(self.request)
                self.request.close()

            def handle(self):
                eprint(f'Connection request from {self.request.getsockname()}')
                with self.request.makefile('wb', buffering=False) as file:
                    self.outer_self.clients[self.outer_self.queue.get()] = file
                    self.outer_self.queue.task_done()
                    self.outer_self.event.wait()

        with ThreadedTCPServer((self.host, findPort()), ThreadedTCPRequestHandler) as server:
            st = Thread(target=server.serve_forever)

            try:
                eprint(f'\nAccepting connections on {server.socket.getsockname()}\n')
                st.start()
                self.__processData(isDead, buffer)
            except (KeyboardInterrupt, TypeError):
                pass
            except Exception as e:
                printException(e)
            finally:
                self.event.set()
                server.shutdown()
                st.join()
                vprint(f'Multi-VFO writer halted')
                return
