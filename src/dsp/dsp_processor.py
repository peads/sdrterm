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
from multiprocessing import Value, Queue
from sys import stdout
from typing import Callable

from numpy import ndarray, dtype, complex64, complex128, float32, float64, pad, exp, arange, pi, array
from scipy.signal import decimate, dlti, savgol_filter

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod
from dsp.util import applyFilters, generateEllipFilter
from misc.general_util import vprint


class DspProcessor(DataProcessor):
    _FILTER_DEGREE = 3

    def __init__(self,
                 fs: int,
                 center: int = 0,
                 omegaOut: int = 0,
                 tuned: int = 0,
                 dec: int = 2,
                 smooth: bool = False,
                 fileInfo: dict = None,
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
        self._isDead = False
        self.__fileInfo = fileInfo
        self.__xSize = -1
        self._pool = None

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

    def demod(self, y: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
        if y.ndim < 2:
            setattr(self, 'demod', self._demod)
            return self._demod(y)
        else:
            ret = array([self._demod(yy) for yy in y])

            def demod(x):
                i = 0
                for val in self._pool.map(self._demod, x):
                    ret[i][:] = val
                    i += 1
                return ret

            setattr(self, 'demod', demod)
            return ret

    def _demod(self, y: ndarray[any, dtype[complex64 | complex128]]) -> ndarray[any, dtype[float32 | float64]]:
        pass

    def __setDemod(self, fun: Callable[
        [ndarray[any, dtype[complex64 | complex128]]], ndarray[any, dtype[float32 | float64]]],
                   *filters) -> Callable[
        [ndarray[any, dtype[complex64 | complex128]]], ndarray[any, dtype[float32 | float64]]]:
        if fun is not None and filters is not None and len(filters) > 0:
            self._outputFilters.clear()
            self._outputFilters.extend(*filters)
            setattr(self, '_demod', fun)
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

    def _processChunk(self, y: ndarray) -> ndarray[any, dtype[float32 | float64]]:
        if self._shift is not None:
            '''
                NOTE: apparently, numpy doesn't override the unary multiplication arithemetic assignment operator the
                same way as the binary multiplication operator for ndarrays. So, this has to remain this way. 
            '''
            y = y * self._shift
        if self._decimationFactor > 1:
            y = decimate(y, self._decimationFactor)
        y = self.demod(y)
        return applyFilters(y, self._outputFilters)

    def _transformData(self, x: ndarray, file) -> None:
        from struct import pack
        y = self._processChunk(x)

        if self.smooth:
            y = savgol_filter(y, self.smooth, self._FILTER_DEGREE)

        file.write(pack('@' + (y.size * 'd'), *y))

    def _processData(self, isDead: Value, buffer: Queue, file) -> None:
        x = None
        while not (self._isDead or isDead.value):
            if x is None:
                x = buffer.get()
                self.__xSize = self.__xSize
            else:
                x[:] = buffer.get()

            if self._shift is None:
                self._generateShift(x.size)

            if x.size < self.__xSize:
                x[:] = pad(x, (0, -x.size + self.__xSize), mode='constant', constant_values=0)

            self._transformData(x, file)

    def _generateShift(self, c: int) -> None:
        if self.centerFreq:
            self._shift = exp(-2j * pi * (self.centerFreq / self.__fs) * arange(c))

    def processData(self, isDead: Value, buffer: Queue, f: str, *args, **kwargs) -> None:
        with open(f, 'wb') if f is not None else open(stdout.fileno(), 'wb', closefd=False) as file:
            try:
                self._processData(isDead, buffer, file)
                file.write(b'')
                file.flush()
            except KeyboardInterrupt:
                pass
            # except Exception as e:
            #     from misc.general_util import printException
            #     printException(e)
            finally:
                buffer.close()
                buffer.join_thread()
                vprint(f'Standard writer halted')
                return

    def __repr__(self):
        from json import dumps
        d = {(key if 'Str' not in key else key[:-3]): value for key, value in self.__dict__.items()
             if not (value is None or key.startswith('_')
                     or callable(value)
                     or issubclass(type(value), ndarray)
                     or issubclass(type(value), dlti)
                     or key in {'outputFilters'})}
        d['encoding'] = str(self.__fileInfo['bitsPerSample'])
        d['fs'] = self.__fs
        d['decimatedFs'] = self.__decimatedFs
        return dumps(d, indent=2)

    def __str__(self):
        return self.__class__.__name__
