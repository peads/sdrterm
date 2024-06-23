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

import typer

from misc.general_util import eprint
from sdr import output_server
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.controller import UnrecognizedInputError
from sdr.rtl_tcp_commands import RtlTcpCommands
from sdr.socket_receiver import SocketReceiver


def main(host: Annotated[str, typer.Argument(help='Address of remote rtl_tcp server')],
         port: Annotated[int, typer.Argument(help='Port of remote rtl_tcp server')],
         server_host: Annotated[str, typer.Option(help='Port of local distribution server')] = 'localhost') -> None:
    isDead = Value('b', 0)
    isDead.value = 0
    with SocketReceiver(isDead=isDead, host=host, port=port) as receiver:
        server, st, pt = output_server.initServer(receiver, isDead, server_host)
        receiver.connect()
        cmdr = ControlRtlTcp(receiver.receiver)
        st.start()
        pt.start()

        try:
            while not isDead.value:
                try:
                    print('Available commands are:\n')
                    [print(f'{e.value}\t{e.name}') for e in RtlTcpCommands]
                    print(f'\nAccepting connections on port {server.socket.getsockname()[1]}\n')
                    inp = input(
                        'Provide a space-delimited, command-value pair (e.g. SET_GAIN 1):\n')
                    if ('q' == inp or 'Q' == inp or 'quit' in inp.lower()
                            or 'exit' in inp.lower()):
                        isDead.value = 1
                        raise KeyboardInterrupt
                    elif ' ' not in inp:
                        print(f'ERROR: Input invalid: {inp}. Please try again')
                    else:
                        (cmd, param) = inp.split()
                        if cmd.isnumeric():
                            numCmd = RtlTcpCommands(int(cmd)).value
                        else:
                            numCmd = RtlTcpCommands[cmd].value
                        if not param.isnumeric():
                            print(f'ERROR: Input invalid: {cmd}: {param}. Please try again')
                        else:
                            param = int(param)
                            cmdr.setParam(numCmd, param)
                            receiver.fs = param
                            if RtlTcpCommands.SET_SAMPLE_RATE.value == numCmd:
                                receiver.buffer = None
                except (UnrecognizedInputError, ValueError, KeyError) as ex:
                    print(f'ERROR: Input invalid: {ex}. Please try again')
        except KeyboardInterrupt:
            pass
        finally:
            isDead.value = 1
            server.shutdown()
            server.server_close()
            st.join(1)
            pt.join(1)
            eprint('UI halted')
            return


if __name__ == "__main__":
    typer.run(main)
