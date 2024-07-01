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
from misc.mappable_enum import MappableEnum


class RtlTcpSamplingRate(MappableEnum):
    fs0 = 250000
    fs1 = 256000
    fs2 = 1024000
    fs3 = 1200000
    fs4 = 2048000
    fs5 = 2400000
    fs6 = 3200000

    @classmethod
    def dict(cls):
        return {str(i.value): i.value for i in cls}

# translated directly from rtl_tcp.c
class RtlTcpCommands(MappableEnum):
    SET_FREQUENCY = 0x01
    SET_SAMPLE_RATE = 0x02
    SET_GAIN_MODE = 0x03
    SET_GAIN = 0x04
    SET_FREQUENCY_CORRECTION = 0x05
    SET_IF_STAGE = 0x06
    SET_TEST_MODE = 0x07
    SET_AGC_MODE = 0x08
    SET_DIRECT_SAMPLING = 0x09
    SET_OFFSET_TUNING = 0x0A
    SET_RTL_CRYSTAL = 0x0B
    SET_TUNER_CRYSTAL = 0x0C
    SET_TUNER_GAIN_BY_INDEX = 0x0D
    SET_BIAS_TEE = 0x0E
    SET_TUNER_BANDWIDTH = 0x40
    UDP_ESTABLISH = 0x41
    UDP_TERMINATE = 0x42
    SET_I2C_TUNER_REGISTER = 0x43
    SET_I2C_TUNER_OVERRIDE = 0x44
    SET_TUNER_BW_IF_CENTER = 0x45
    SET_TUNER_IF_MODE = 0x46
    SET_SIDEBAND = 0x47
    REPORT_I2C_REGS = 0x48
    GPIO_SET_OUTPUT_MODE = 0x49
    GPIO_SET_INPUT_MODE = 0x50
    GPIO_GET_IO_STATUS = 0x51
    GPIO_WRITE_PIN = 0x52
    GPIO_READ_PIN = 0x53
    GPIO_GET_BYTE = 0x54
    IS_TUNER_PLL_LOCKED = 0x55
    SET_FREQ_HI32 = 0x56

    def __str__(self):
        return self.name
    def __repr__(self):
        return self.__str__()
