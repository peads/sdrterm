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
from multiprocessing import Value
from typing import Annotated

from typer import run as typerRun, Argument, Option

from misc.general_util import vprint, printException
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.controller import UnrecognizedInputError
from sdr.output_server import OutputServer
from sdr.rtl_tcp_commands import RtlTcpCommands
from sdr.socket_receiver import SocketReceiver


def main(host: Annotated[str, Argument(help='Address of remote rtl_tcp server')],
         port: Annotated[int, Argument(help='Port of remote rtl_tcp server')],
         server_host: Annotated[str, Option(help='Port of local distribution server')] = 'localhost') -> None:
    isDead = Value('b', 0)
    isDead.value = 0

    with SocketReceiver(isDead=isDead, host=host, port=port) as receiver:
        with OutputServer(receiver, server_host) as server:
            cmdr = ControlRtlTcp(receiver, receiver.reset)

            try:
                while not isDead.value:
                    try:
                        print('Available commands are:\n')
                        [print(f'{e.value}\t{e.name}') for e in RtlTcpCommands]
                        print(f'\nAccepting connections on port {server.socket.getsockname()}\n')
                        inp = input(
                            'Provide a space-delimited, command-value pair (e.g. SET_GAIN 1):\n')
                        if ('q' == inp or 'Q' == inp or 'quit' in inp.lower()
                                or 'exit' in inp.lower()):
                            break
                        elif ' ' not in inp:
                            print(f'ERROR: Input invalid: {inp}. Please try again')
                        else:
                            (cmd, param) = inp.split()
                            if cmd.isnumeric():
                                numCmd = RtlTcpCommands(int(cmd))
                            else:
                                numCmd = RtlTcpCommands[cmd]

                            if not (('-' in param or param.isnumeric())
                                    and (len(param) < 2 or param[1:].isnumeric())):
                                print(f'ERROR: Input invalid: {cmd}: {param}. Please try again')
                            else:
                                param = int(param)
                                cmdr.setParam(numCmd, param)
                    except (UnrecognizedInputError, ValueError, KeyError) as ex:
                        print(f'ERROR: Input invalid: {ex}. Please try again')
            except (KeyboardInterrupt, EOFError):
                pass
            except Exception as e:
                printException(e)
            finally:
                isDead.value = 1
                server.shutdown()
                vprint('UI halted')
                return


if __name__ == "__main__":
    typerRun(main)
