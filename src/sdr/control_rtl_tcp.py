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
from socket import socket
from struct import error as StructError, pack
from typing import Callable

from sdr.controller import Controller
from sdr.controller import UnrecognizedInputError
from sdr.rtl_tcp_commands import RtlTcpCommands


class ControlRtlTcp(Controller):
    def __init__(self, connection: socket, resetBuffers: Callable[[int], None] = lambda: None):
        super().__init__(connection)
        self._resetBuffers = resetBuffers
        # if resetBuffers is not None:
        #     setattr(self, 'resetBuffers', resetBuffers)
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_GAIN_MODE.value, 1))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_AGC_MODE.value, 0))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, 0))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_SAMPLE_RATE.value, 1024000))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_BIAS_TEE.value, 0))

    @property
    def resetBuffers(self) -> Callable[[int], None]:
        return self._resetBuffers

    @resetBuffers.setter
    def resetBuffers(self, resetBuffers: Callable[[int], None]) -> None:
        self._resetBuffers = resetBuffers

    @resetBuffers.deleter
    def resetBuffers(self) -> None:
        del self._resetBuffers

    def setFrequency(self, freq: int) -> None:
        self.setParam(RtlTcpCommands.SET_FREQUENCY, freq)

    def setFs(self, fs: int) -> None:
        self.setParam(RtlTcpCommands.SET_SAMPLE_RATE, fs)

    def setParam(self, command: RtlTcpCommands, param: int) -> None:
        if self.connection is not None:
            print(f'{RtlTcpCommands(command)}: {param}')
            try:
                if '-' in hex(param):
                    self.connection.sendall(pack('!Bi', command.value, param))
                else:
                    self.connection.sendall(pack('!BI', command.value, param))

                if RtlTcpCommands.SET_SAMPLE_RATE == command:
                    self.resetBuffers(param)
                    self.connection.sendall(pack('!BI', RtlTcpCommands.SET_TUNER_BANDWIDTH.value, param))
            except StructError as e:
                raise UnrecognizedInputError(f'{command}: {param}', e)
