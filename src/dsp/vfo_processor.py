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
from io import RawIOBase
from multiprocessing import Value
from queue import Queue
from socketserver import ThreadingMixIn, TCPServer, BaseRequestHandler
from threading import Thread, Event

from numpy import pi, array, complex128, exp, arange, ones

from dsp.dsp_processor import DspProcessor
from misc.general_util import eprint, findPort, tprint, vprint, shutdownSocket


class ThreadedTCPServer(ThreadingMixIn, TCPServer):
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
        if ':' in vfoHost:
            self.host, self.port = vfoHost.split(':')
            self.port = int(self.port)
        else:
            self.host = vfoHost
            self.port = findPort(self.host)
        self.__queue: Queue[int, ...] | None = None
        self.__clients: dict[str, RawIOBase] | None = None
        self.__event: Event | None = None

    @property
    def clients(self) -> dict[str, RawIOBase]:
        return self.__clients

    @property
    def event(self) -> Event:
        return self.__event

    @property
    def queue(self) -> Queue[int, ...]:
        return self.__queue

    def _generateShift(self, c: int) -> None:
        self._shift = ones(shape=(self._nFreq, c), dtype=complex128)
        for i, w in enumerate(self.__omega):
            self._shift[i][:] = exp(w * arange(c))
            self.queue.put(w)
            tprint(f'Put {w}')
        self.queue.join()
        eprint('Connection(s) established')

    def _transformData(self, x, y, z, _=None) -> None:
        from struct import pack
        self._processChunk(x, y, z)
        for (request, data) in zip(self.__clients.values(), z):
            request.write(pack('!' + str(data.size) + 'd', *data))

    def processData(self, isDead: Value, buffer: Queue, *args, **kwargs) -> None:
        self.__queue = Queue()
        self.__event = Event()
        self.__clients = {}

        class ThreadedTCPRequestHandler(BaseRequestHandler):
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

        with ThreadedTCPServer((self.host, self.port), ThreadedTCPRequestHandler) as server:
            st = Thread(target=server.serve_forever)

            try:
                eprint(f'\nAccepting connections on {server.socket.getsockname()}\n')
                st.start()
                self._processData(isDead, buffer)
            except KeyboardInterrupt:
                pass
            # except BaseException as e:
            #     from misc.general_util import printException
            #     printException(e)
            finally:
                self.__event.set()
                self._isDead = True
                server.shutdown()
                with self.__queue.all_tasks_done:
                    self.__queue.all_tasks_done.notify_all()
                st.join()
                vprint('Multi-VFO writer halted')
                return
