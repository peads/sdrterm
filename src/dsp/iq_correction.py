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
from numba import complex128, uint64, float64, prange
from numba.experimental import jitclass
from numpy import ndarray, dtype, complexfloating


@jitclass([
    ('_sampRate', uint64),
    ('_inductance', float64),
    ('_off', complex128)])
class IQCorrection:
    def __init__(self, sampRate: int, impedance: int = 50):
        self._sampRate = sampRate
        self._inductance = impedance / sampRate
        self._off = 0j

    @property
    def sampleRate(self):
        return self._sampRate

    @sampleRate.setter
    def sampleRate(self, sampRate: int):
        self._inductance = self._inductance * self._sampRate
        self._sampRate = sampRate
        self._inductance /= self._sampRate
        self._off = 0j

    @property
    def inductance(self):
        return self._inductance

    @inductance.setter
    def inductance(self, impedance: int):
        self._inductance = impedance / self._sampRate
        self._off = 0j

    def correctIq(self, data: ndarray[any, dtype[complexfloating]]) -> None:
        for i in prange(len(data)):
            data[i] -= self._off
            self._off += data[i] * self._inductance
