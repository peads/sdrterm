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
import socketserver
from contextlib import closing
from multiprocessing import Value
from queue import Queue

from misc.general_util import shutdownSocket, eprint
from misc.hooked_thread import HookedThread
from sdr.receiver import Receiver


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost') -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def log(*args, **kwargs) -> None:
    eprint(*args, **kwargs)

def initServer(receiver: Receiver, isDead: Value, host='localhost', port=findPort()):
    clients = []
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        pass

    class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):

        def setup(self):
            if not receiver.barrier.broken:
                receiver.barrier.wait()

        def handle(self):
            log(f'Connection request from {self.request.getsockname()}')
            buffer = Queue(16)
            clients.append(buffer)
            while not isDead.value:
                try:
                    data = buffer.get()
                    self.request.sendall(data)
                    buffer.task_done()
                except (ValueError, ConnectionError, EOFError):
                    log(f'Client disconnected: {self.request.getsockname()}')
                    shutdownSocket(self.request)
                    clients.remove(buffer)
                    break
            del buffer

    def receive():
        if not receiver.barrier.broken:
            receiver.barrier.wait()
            receiver.barrier.abort()
        while not isDead.value:
            data = receiver.receive()
            for client in list(clients):
                client.put(data)

    server = ThreadedTCPServer((host, port), ThreadedTCPRequestHandler)
    st = HookedThread(isDead, target=server.serve_forever, daemon=True)
    rt = HookedThread(isDead, target=receive, daemon=True)
    return server, st, rt
