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
from socketserver import BaseRequestHandler, ThreadingMixIn, TCPServer

from misc.general_util import shutdownSocket, eprint, findPort
from misc.keyboard_interruptable_thread import KeyboardInterruptableThread
from sdr.socket_receiver import SocketReceiver


def log(*args, **kwargs) -> None:
    eprint(*args, **kwargs)


class OutputServer(ThreadingMixIn, TCPServer):
    def __init__(self, receiver: SocketReceiver, server_host: str, *args, **kwargs):
        class ThreadedTCPRequestHandler(BaseRequestHandler):
            def finish(self):
                log(f'Client disconnected: {self.request.getsockname()}')
                shutdownSocket(self.request)
                self.request.close()

            def handle(self):
                log(f'Connection request from {self.request.getsockname()}')
                with self.request.makefile('wb', buffering=False) as file:
                    receiver.addClient(file).wait()
                return

        super().__init__((server_host, findPort(server_host)), ThreadedTCPRequestHandler, *args, **kwargs)

        self.receiver = receiver
        self.pt = KeyboardInterruptableThread(self.shutdown, target=receiver.receive)
        self.st = KeyboardInterruptableThread(self.shutdown, target=self.serve_forever)

    def __enter__(self):
        super().__enter__()
        self.pt.start()
        self.st.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.receiver.disconnect()
        self.pt.join(5)
        self.st.join(5)
        super().__exit__(*args, **kwargs)
