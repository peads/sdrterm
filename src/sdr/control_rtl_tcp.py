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
from struct import error as StructError, pack

from sdr.controller import Controller
from sdr.controller import UnrecognizedInputError
from sdr.rtl_tcp_commands import RtlTcpCommands


class ControlRtlTcp(Controller):
    def __init__(self, connection):
        super().__init__(connection)
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_GAIN_MODE.value, 1))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_AGC_MODE.value, 0))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, 0))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_SAMPLE_RATE.value, 1024000))
        # connection.sendall(pack('>BI', RtlTcpCommands.SET_BIAS_TEE.value, 0))

    def setFrequency(self, freq):
        self.setParam(RtlTcpCommands.SET_FREQUENCY.value, freq)

    def setFs(self, fs):
        self.setParam(RtlTcpCommands.SET_SAMPLE_RATE.value, fs)

    def setParam(self, command, param):
        print(f'{RtlTcpCommands(command)}: {param}')
        try:
            if '-' in hex(param):
                self.connection.sendall(pack('>Bi', command, param))
            else:
                self.connection.sendall(pack('>BI', command, param))
        except StructError as e:
            raise UnrecognizedInputError(param, e)
