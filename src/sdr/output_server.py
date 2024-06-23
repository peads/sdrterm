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
import sys
import threading
from multiprocessing import Value
from queue import Queue

from misc.general_util import shutdownSocket, eprint, findPort
from misc.hooked_thread import HookedThread
from sdr.socket_receiver import SocketReceiver


def log(*args, **kwargs) -> None:
    eprint(*args, **kwargs)


def initServer(receiver: SocketReceiver, isDead: Value, server_host: str) \
        -> tuple[socketserver.TCPServer, HookedThread, HookedThread]:
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
                except (ConnectionError, EOFError, ValueError) as e:
                    log(f'Client disconnected: {self.request.getsockname()}: {e}')
                    clients.remove(buffer)
                    break
            shutdownSocket(self.request)
            self.request.close()
            buffer.join()
            return

    def receive():
        if not receiver.barrier.broken:
            receiver.barrier.wait()
            receiver.barrier.abort()
        while not isDead.value:
            data = receiver.receive()
            for y in data:
                for client in list(clients):
                    client.put(y)
        return

    server = ThreadedTCPServer((server_host, findPort()), ThreadedTCPRequestHandler)
    class ServerHookedThread(HookedThread):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            def handleException(e, *argv):
                isDead.value = 1
                receiver.disconnect()
                for client in list(clients):
                    clients.remove(client)
                    client.join()
                if issubclass(type(e), KeyboardInterrupt):
                    sys.__excepthook__(e, *argv)
                return

            threading.excepthook = handleException

    st = ServerHookedThread(isDead, target=server.serve_forever, daemon=True)
    rt = ServerHookedThread(isDead, target=receive, daemon=True)
    return server, st, rt
