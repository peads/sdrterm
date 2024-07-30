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
# cython: profile=False
# cython: nonecheck=False
# cython: boundscheck=False
# cython: overflowcheck=False
# cython: overflowcheck.fold=False
# cython: language_level=3
# cython: infer_types=False
# TODO remove and append EVERY SINGLE CDEF LINE with noexcept, when this is finally removed.
# cython: legacy_no_except=True
# cython: show_performance_hints=True
# cython: freethreading_compatible=True
# cython: cpow=True

cimport cython
cimport numpy as np; np.import_array()
from numpy cimport ndarray

cdef class IQCorrection:
    cdef unsigned long _fs
    cdef readonly double inductance

    def __cinit__(self, const unsigned long fs, const unsigned short impedance = 50):
        self._fs = fs
        self.inductance = impedance / fs

    @cython.cdivision(True)
    cpdef void correctIq(self, ndarray[np.complex128_t] data, ndarray[np.complex128_t] off):
        cdef Py_ssize_t i
        cdef Py_ssize_t size = data.shape[0]
        with nogil:
            for i in range(size):
                data[i] = data[i] - off[0]
                off[0] += data[i] * self.inductance

    @property
    def fs(self):
        return self._fs

    @fs.setter
    def fs(self, unsigned long fs):
        self.inductance = self.impedance
        self._fs = fs
        self.inductance = self.inductance / fs

    @property
    def impedance(self):
        return self.inductance * self._fs

    @impedance.setter
    def impedance(self, const unsigned short impedance):
        self.inductance = impedance / self._fs
