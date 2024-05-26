#!/usr/bin/env python3
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
from contextlib import closing
from multiprocessing import Value
from typing import Annotated

import typer

from misc.general_util import applyIgnoreException, printException, eprint
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.control_rtl_tcp import UnrecognizedInputError
from sdr.output_server import OutputServer, Receiver
from sdr.rtl_tcp_commands import RtlTcpCommands


class __SocketReceiver(Receiver):

    def __init__(self, receiver: socket.socket,
                 writeSize=262144, readSize=8192):
        super().__init__(receiver)
        self.readSize = readSize
        self.data = bytearray()
        self.chunks = range(writeSize // readSize)

    def receive(self):
        if not self._barrier.broken:
            self._barrier.wait()
            self._barrier.abort()
        for _ in self.chunks:
            try:
                inp = self.receiver.recv(self.readSize)
            except BrokenPipeError:
                return b''
            if inp is None or not len(inp):
                break
            self.data.extend(inp)
        result = bytes(self.data)
        self.data.clear()
        return result


def main(host: Annotated[str, typer.Argument(help='Address of remote rtl_tcp server')],
         port: Annotated[int, typer.Argument(help='Port of remote rtl_tcp server')]) -> None:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as recvSckt:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listenerSckt:
            recvSckt.settimeout(1)
            recvSckt.connect((host, port))
            cmdr = ControlRtlTcp(recvSckt)
            isDead = Value('b', 0)
            isDead.value = 0
            server = OutputServer(host='0.0.0.0')

            st, pt = server.initServer(__SocketReceiver(recvSckt), listenerSckt, isDead)
            pt.start()
            st.start()

            try:
                while not isDead.value:
                    try:
                        print('Available commands are:\n')
                        [print(f'{e.value}\t{e.name}') for e in RtlTcpCommands]
                        print(f'\nAccepting connections on port {server.port}\n')
                        inp = input(
                            'Provide a space-delimited, command-value pair (e.g. SET_GAIN 1):\n')
                        if ('q' == inp or 'Q' == inp or 'quit' in inp.lower()
                                or 'exit' in inp.lower()):
                            isDead.value = 1
                        elif ' ' not in inp:
                            print(f'ERROR: Input invalid: {inp}. Please try again')
                        else:
                            (cmd, param) = inp.split()
                            if cmd.isnumeric():
                                numCmd = RtlTcpCommands(int(cmd)).value
                            else:
                                numCmd = RtlTcpCommands[cmd].value

                            if param.isnumeric():
                                cmdr.setParam(numCmd, int(param))
                            else:
                                print(f'ERROR: Input invalid: {cmd}: {param}. Please try again')
                    except (UnrecognizedInputError, ValueError, KeyError) as ex:
                        print(f'ERROR: Input invalid: {ex}. Please try again')
            except (ConnectionResetError, ConnectionAbortedError):
                eprint(f'Connection lost')
            except Exception as e:
                printException(e)
            finally:
                isDead.value = 1
                applyIgnoreException(lambda: recvSckt.shutdown(socket.SHUT_RDWR))
                applyIgnoreException(lambda: listenerSckt.shutdown(socket.SHUT_RDWR))
                st.join(0.1)
                pt.join(0.1)
                print('UI halted')


if __name__ == "__main__":
    typer.run(main)
