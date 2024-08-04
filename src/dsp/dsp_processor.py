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
from typing import Callable, Iterable, Any

from numpy import ndarray, dtype, complex128, float64, exp, arange, pi, empty, array
from scipy.signal import decimate, dlti, savgol_filter, sosfilt, ellip

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod, realOutput, imagOutput, shiftFreq
from misc.general_util import vprint


def applyFilters(y: ndarray | Iterable, *filters) -> ndarray[
    any, dtype[float64 | complex128]]:
    for sos in filters:
        y = sosfilt(sos, y)
    return y


def generateEllipFilter(fs: int, deg: int, Wn: float | Iterable[float], btype: str) -> tuple[
    any, float, any]:
    return ellip(deg, 1, 30, Wn,
                 btype=btype,
                 analog=False,
                 output='sos',
                 fs=fs)


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

        self._demod = None
        self._shift = None
        self.bandwidth = None
        self.__fs = None
        self.__decimatedFs = None
        self._isDead = False
        self._outputFilters = []
        self.tmp = None
        self._nFreq = 1

        self._decimationFactor = dec
        self.fs = fs
        self.centerFreq = center
        self.tunedFreq = tuned
        self.omegaOut = omegaOut
        self.smooth = smooth
        self.__fileInfo = fileInfo

    @property
    def fs(self) -> int:
        return self.__fs

    @fs.setter
    def fs(self, fs: int) -> None:
        self.__fs = fs
        self.__decimatedFs = fs // self._decimationFactor

    @property
    def decimation(self) -> int:
        return self._decimationFactor

    @decimation.setter
    def decimation(self, decimation: int) -> None:
        if decimation < 2:
            raise ValueError("Decimation must be at least 2.")
        self._decimationFactor = decimation
        self.fs = self.__fs

    @property
    def decimatedFs(self) -> int:
        return self.__decimatedFs

    def demod(self, *_, **__):
        pass

    def _setDemod(self, fun: Callable[[ndarray, ndarray], None], *filters) \
            -> Callable[[tuple[Any, ...], dict[str, Any]], None]:
        if fun is not None:
            self._outputFilters.clear()
            if len(filters):
                self._outputFilters.extend(*filters)
            setattr(self, 'demod', fun)
            return self.demod
        raise ValueError("Demodulation function, or filters not defined")

    def selectOutputFm(self):
        vprint('NFM Selected')
        self.bandwidth = 12500
        self._setDemod(fmDemod,
                       generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, self.omegaOut,
                                           'lowpass'))

    def selectOutputAm(self):
        vprint('AM Selected')
        self.bandwidth = 10000
        self._setDemod(amDemod,
                       generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, self.omegaOut,
                                           'lowpass'))

    def selectOutputReal(self):
        vprint('I output Selected')
        self.bandwidth = self.decimatedFs
        self._setDemod(realOutput)

    def selectOutputImag(self):
        vprint('Q output Selected')
        self.bandwidth = self.decimatedFs
        self._setDemod(imagOutput)

    def _processChunk(self,
                      x: ndarray[any, dtype[complex128]],
                      y: ndarray[any, dtype[complex128]],
                      z: ndarray[any, dtype[float64]]) -> None:
        if self._shift is not None:
            shiftFreq(x[0], self._shift, x)
            # y = y * self._shift
        y[:] = decimate(x, self._decimationFactor)
        self.demod(y, z)
        z[:] = applyFilters(z, self._outputFilters)

    def _transformData(self,
                       x: ndarray[any, dtype[complex128]],
                       y: ndarray[any, dtype[complex128]],
                       z: ndarray[any, dtype[float64]],
                       file) -> None:
        from struct import pack
        self._processChunk(x, y, z)

        if self.smooth:
            z[:] = savgol_filter(z, self.smooth, self._FILTER_DEGREE)

        file.write(pack('@' + (z.size * 'd'), *z.flat))

    def _processData(self, isDead: Value, buffer: Queue, file=None) -> None:
        x = None
        y = None
        z = None
        while not (self._isDead or isDead.value):
            if x is not None:
                x[0, :] = buffer.get()
            else:
                x = buffer.get()
                shape = (self._nFreq, x.size // self._decimationFactor)
                tmp = empty((self._nFreq, x.size), dtype=x.dtype)
                tmp[0, :] = x
                x = tmp
                y = empty(shape, dtype=x.dtype)
                z = empty(shape, dtype=float64)

            if self._shift is None:
                self._generateShift(x.shape[1])

            self._transformData(x, y, z, file)

    def _generateShift(self, c: int) -> None:
        if self.centerFreq:
            self._shift = array([exp(-2j * pi * (self.centerFreq / self.__fs) * arange(c))])

    def processData(self, isDead: Value, buffer: Queue, f: str, *args, **kwargs) -> None:
        with open(f, 'wb') if f is not None else open(stdout.fileno(), 'wb', closefd=False) as file:
            try:
                self._processData(isDead, buffer, file)
                file.write(b'')
                file.flush()
            except KeyboardInterrupt:
                pass
            # except BaseException as e:
            #     from misc.general_util import printException
            #     printException(e)
            finally:
                buffer.close()
                buffer.join_thread()
                vprint('Standard writer halted')
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

# def generateDeemphFilter(fs: float, f: float = 7.5e-5) -> ndarray[any, dtype[float64]]:
#     alpha = 1 / (1 - exp(-26666.7 / (f * fs)))
#     B = [alpha, 1]
#     A = [1]
#     return tf2sos(B, A)

# def generateDcBlock():
#     return tf2sos([1, 0, 0, 0, 0, 1], [1, 0, 0, 0, 0, .95], analog=False)

# def rms(inp):
#     def func(a):
#         return sqrt(-square(sum(a)) + len(a) * sum(a * a)) / len(a)
#
#     ret = apply_along_axis(func, -1, inp)
#     return ret
