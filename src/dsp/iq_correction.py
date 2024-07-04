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
# from dsp.util import quadwise
from numpy import ndarray, dtype, complex64, complex128


class IQCorrection:
    def __init__(self, sampRate: int, impedance: int = 50):
        self.__sampRate = sampRate
        self.__inductance = impedance / sampRate
        self.__off = 0 + 0j

    @property
    def sampleRate(self):
        return self.__sampRate

    @sampleRate.setter
    def sampleRate(self, sampRate: int):
        self.__inductance = self.__inductance * self.__sampRate
        self.__sampRate = sampRate
        self.__inductance /= self.__sampRate
        self.__off = 0j

    @sampleRate.deleter
    def sampleRate(self):
        del self.__sampRate

    @property
    def inductance(self):
        return self.__inductance

    @inductance.setter
    def inductance(self, impedance: int):
        self.__inductance = impedance / self.__sampRate
        self.__off = 0j

    @inductance.deleter
    def inductance(self):
        del self.__inductance

    def correctIq(self, data: ndarray[any, dtype[complex64 | complex128]]) -> None:
        for i in range(len(data)):
            data[i] -= self.__off
            self.__off += data[i] * self.__inductance
