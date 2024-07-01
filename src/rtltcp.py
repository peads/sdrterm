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

import numpy as np
import typer

from misc.general_util import vprint, printException
from sdr import output_server
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.controller import UnrecognizedInputError
from sdr.rtl_tcp_commands import RtlTcpCommands
from sdr.socket_receiver import SocketReceiver


def main(host: Annotated[str, typer.Argument(help='Address of remote rtl_tcp server')],
         port: Annotated[int, typer.Argument(help='Port of remote rtl_tcp server')],
         server_host: Annotated[str, typer.Option(help='Port of local distribution server')] = 'localhost') -> None:
    from os import getpid
    isDead = Value('b', 0)
    isDead.value = 0
    pid = getpid()

    with SocketReceiver(isDead=isDead, host=host, port=port) as receiver:
        server, st, pt, resetBuffers = output_server.initServer(receiver, isDead, server_host)
        receiver.connect()

        # def stopProcessing(sig: int = None):
        #     if sig is not None:
        #         from signal import Signals
        #         eprint(f'pid: {pid} stopping processing due to {Signals(sig).name}')
        #     isDead.value = 1
        #     server.shutdown()
        #     server.server_close()
        #
        # setSignalHandlers(pid, stopProcessing)

        def reset(fs: int):
            resetBuffers()
            receiver.reset(None if fs > receiver.BUF_SIZE else (1 << int(np.log2(fs))))

        cmdr = ControlRtlTcp(receiver.receiver, reset)
        pt.start()
        st.start()

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
                        # isDead.value = 1
                        # raise KeyboardInterrupt
                    elif ' ' not in inp:
                        print(f'ERROR: Input invalid: {inp}. Please try again')
                    else:
                        (cmd, param) = inp.split()
                        if cmd.isnumeric():
                            numCmd = RtlTcpCommands(int(cmd)).value
                        else:
                            numCmd = RtlTcpCommands[cmd].value

                        if not (('-' in param or param.isnumeric())
                                and (len(param) < 2 or param[1:].isnumeric())):
                            print(f'ERROR: Input invalid: {cmd}: {param}. Please try again')
                        else:
                            param = int(param)
                            cmdr.setParam(numCmd, param)
                except (UnrecognizedInputError, ValueError, KeyError) as ex:
                    print(f'ERROR: Input invalid: {ex}. Please try again')
        except (KeyboardInterrupt | EOFError):
            pass
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            receiver.disconnect()
            server.shutdown()
            server.server_close()
            st.join(5)
            pt.join(5)
            vprint('UI halted')
            return


if __name__ == "__main__":
    typer.run(main)
