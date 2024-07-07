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
import json
import multiprocessing
import os
import struct
import sys
from multiprocessing import Value, Queue
from typing import Callable

from numpy import ndarray, dtype, complex64, complex128, real, pad, broadcast_to, exp, arange, pi
from scipy.signal import decimate, dlti, savgol_filter

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod
from dsp.util import applyFilters, generateEllipFilter
from misc.general_util import printException, vprint, eprint


class DspProcessor(DataProcessor):
    _FILTER_DEGREE = 3

    def __init__(self,
                 fs: int,
                 center: int = 0,
                 omegaOut: int = 0,
                 tuned: int = 0,
                 dec: int = 2,
                 smooth: bool = False,
                 **kwargs):

        self.bandwidth \
            = self.__fs \
            = self.__dt \
            = self.__decimatedFs \
            = self.__decDt \
            = self._aaFilter = None
        self._outputFilters = []
        self._decimationFactor = dec
        self.fs = fs
        self.centerFreq = center
        self.tunedFreq = tuned
        self.omegaOut = omegaOut
        self.smooth = smooth
        self._shift = None
        self._Y = None
        self._nCpus = os.cpu_count()
        self._ii = range(self._nCpus)
        self._isDead = False

    @property
    def fs(self):
        return self.__fs

    @fs.setter
    def fs(self, fs: int):
        self.__fs = fs
        self.__dt = 1 / fs
        self.__decimatedFs = fs // self._decimationFactor
        self.__decDt = self._decimationFactor * self.__dt

    @fs.deleter
    def fs(self):
        del self.__fs
        del self.__dt
        del self.__decimatedFs
        del self.__decDt

    @property
    def decimation(self):
        return self._decimationFactor

    @decimation.deleter
    def decimation(self):
        del self._decimationFactor

    @decimation.setter
    def decimation(self, decimation: int):
        if decimation < 2:
            raise ValueError("Decimation must be at least 2.")
        self._decimationFactor = decimation
        self.fs = self.__fs

    @property
    def decimatedFs(self):
        return self.__decimatedFs

    @decimatedFs.setter
    def decimatedFs(self, _):
        raise NotImplementedError('Setting the decimatedFs directly is not supported. Set fs instead')

    def demod(self, y: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[real]]:
        pass

    def __setDemod(self, fun: Callable[
        [ndarray[any, dtype[complex64 | complex128]]], ndarray[any, dtype[real]]],
                   *filters) -> Callable[[ndarray[any, dtype[complex64 | complex128]]], ndarray[any, dtype[real]]]:
        if fun is not None and filters is not None and len(filters) > 0:
            self._outputFilters.clear()
            self._outputFilters.extend(*filters)
            setattr(self, 'demod', fun)
            # self._aaFilter = (
            #     ellip(self._FILTER_DEGREE << 1, 0.5, 10,
            #                  Wn=self.bandwidth,
            #                  btype='lowpass',
            #                  analog=False,
            #                  output='zpk',
            #                  fs=self.__fs))
            # self._aaFilter = ZerosPolesGain(*self._aaFilter, dt=self.__dt)
            return self.demod
        raise ValueError("Demodulation function, or filters not defined")

    def selectOuputFm(self):
        vprint('NFM Selected')
        self.bandwidth = 12500
        self.__setDemod(fmDemod, generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, self.omegaOut, 'lowpass'))

    def selectOuputWfm(self):
        vprint('WFM Selected')
        self.bandwidth = 25000
        self.__setDemod(fmDemod, generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, 18000, 'lowpass'))

    def selectOuputAm(self):
        vprint('AM Selected')
        self.bandwidth = 10000
        self.__setDemod(amDemod, generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, 18000, 'lowpass'))

    def _demod(self, y: ndarray):
        return [self.demod(yy) for yy in y]

    def _processChunk(self, y: ndarray) -> ndarray[any, dtype[real]]:
        if self._shift is not None:
            '''
                NOTE: apparently, numpy doesn't override the unary multiplication arithemetic assignment operator the
                same way as the binary multiplication operator for ndarrays. So, this has to remain this way. 
            '''
            y = y * self._shift
        if self._decimationFactor > 1:
            y = decimate(y, self._decimationFactor)#, ftype=self._aaFilter)
        y = self._demod(y)
        return applyFilters(y, self._outputFilters)

    def _bufferChunk(self, isDead: Value, buffer: Queue) -> ndarray[any, dtype[real]]:
        for i in self._ii:
            y = buffer.get()
            if y is None or not len(y) or isDead.value:
                self._isDead = True
                break
            if self._Y is None:
                self._Y = ndarray(shape=(self._nCpus, y.size), dtype=complex128)
            if self._shift is None:
                self._generateShift(self._nCpus, y.size)
            if len(y) < self._Y.shape[1]:
                y = pad(y, (0, -len(y) + self._Y.shape[1]), mode='constant', constant_values=0)
            self._Y[i] = y
        return self._processChunk(self._Y)

    def __processData(self, isDead: Value, buffer: Queue, file):
        while not (self._isDead or isDead.value):
            y = self._bufferChunk(isDead, buffer)
            size = y.size
            y = y.flat
            if self.smooth:
                y = savgol_filter(y, self.smooth, self._FILTER_DEGREE)
            file.write(struct.pack('@' + (size * 'd'), *y))

    def _generateShift(self, r: int, c: int) -> None:
        if self.centerFreq:
            self._shift = broadcast_to(exp(-2j * pi * (self.centerFreq / self.__fs) * arange(c)), (r, c))

    def processData(self, isDead: Value, buffer: Queue, f: str, *args, **kwargs) -> None:
        with open(f, 'wb') if f is not None else open(sys.stdout.fileno(), 'wb', closefd=False) as file:
            try:
                self.__processData(isDead, buffer, file)
                file.write(b'')
                file.flush()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                eprint(f'Process {multiprocessing.current_process().name} raised exception')
                printException(e)
            finally:
                buffer.close()
                buffer.join_thread()
                vprint(f'Standard writer halted')
                return

    def __repr__(self):
        d = {(key if 'Str' not in key else key[:-3]): value for key, value in self.__dict__.items()
             if not (key.startswith('_')
                     or callable(value)
                     or issubclass(type(value), ndarray)
                     or issubclass(type(value), dlti)
                     or key in {'outputFilters'})}
        d['fs'] = self.__fs
        d['decimatedFs'] = self.__decimatedFs
        return json.dumps(d, indent=2)

    def __str__(self):
        return self.__class__.__name__
