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
from threading import Condition
from typing import Annotated

import typer

from exceptions.server_interrupt import ServerInterruptError
from exceptions.unrecognized_input import UnrecognizedInputError
from misc.general_util import applyIgnoreException, printException
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.output_server import OutputServer
from sdr.rtl_tcp_commands import RtlTcpCommands


def main(host: Annotated[str, typer.Argument(help='Address of remote rtl_tcp server')],
         port: Annotated[int, typer.Argument(help='Port of remote rtl_tcp server')]) -> None:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as signalSckt:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as outputSckt:
            signalSckt.connect((host, port))
            cmdr = ControlRtlTcp(signalSckt)
            isDead = Value('b', 0)
            isDead.value = 0
            isConnected = Condition()
            server = OutputServer(host='0.0.0.0')

            with isConnected:
                st, pt = server.initServer(signalSckt, outputSckt, isConnected, isDead)
                st.start()
                isConnected.wait()
                pt.start()
            del isConnected

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
            except Exception as e:
                printException(e)
            finally:
                isDead.value = 1
                applyIgnoreException(lambda: signalSckt.shutdown(socket.SHUT_RDWR))
                applyIgnoreException(lambda: outputSckt.shutdown(socket.SHUT_RDWR))
                st.join(0.1)
                pt.join(0.1)
                print('UI halted')


if __name__ == "__main__":
    try:
        typer.run(main)
    except ServerInterruptError:
        pass
