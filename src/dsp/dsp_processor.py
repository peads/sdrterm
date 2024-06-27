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

import numpy as np
from scipy import signal

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod
from dsp.iq_correction import IQCorrection
from dsp.util import applyFilters, generateEllipFilter
from misc.general_util import printException, vprint, eprint


class DspProcessor(DataProcessor):
    _FILTER_DEGREE = 3

    def __init__(self,
                 fs: int,
                 center: int = 0,
                 omegaOut: int = 0,
                 tuned: int = 0,
                 correctIq: bool = False,
                 dec: int = 2,
                 smooth: bool = False,
                 cpus: int = 1,
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
        if correctIq:
            setattr(self, 'correctIq', IQCorrection(self.__decimatedFs).correctIq)
        self.smooth = smooth

        self._nCpus = os.cpu_count()
        self._ii = range(self._nCpus)

    @staticmethod
    def correctIq(y):
        return y

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
        if not decimation or decimation < 2:
            raise ValueError("Decimation must be at least 2.")
        self._decimationFactor = decimation
        self.fs = self.__fs
        setattr(self, 'correctIq', IQCorrection(self.__decimatedFs).correctIq)

    @property
    def decimatedFs(self):
        return self.__decimatedFs

    @decimatedFs.setter
    def decimatedFs(self, _):
        raise NotImplementedError('Setting the decimatedFs directly is not supported. Set fs instead')

    def demod(self, y: np.ndarray[any, np.dtype[np.complex64 | np.complex128]]) -> np.ndarray[any, np.dtype[np.real]]:
        pass

    def __setDemod(self, fun: Callable[
        [np.ndarray[any, np.dtype[np.complex64 | np.complex128]]], np.ndarray[any, np.dtype[np.real]]],
                   *filters) \
            -> Callable[[np.ndarray[any, np.dtype[np.complex64 | np.complex128]]], np.ndarray[any, np.dtype[np.real]]]:
        if fun is not None and filters is not None and len(filters) > 0:
            self._outputFilters.clear()
            self._outputFilters.extend(*filters)
            setattr(self, 'demod', fun)
            self._aaFilter = (
                signal.ellip(self._FILTER_DEGREE << 1, 0.5, 10,
                                          Wn=self.bandwidth,
                                          btype='lowpass',
                                          analog=False,
                                          output='zpk',
                                          fs=self.__fs))
            self._aaFilter = signal.ZerosPolesGain(*self._aaFilter, dt=self.__dt)
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

    def _demod(self, y: np.ndarray):
        return [self.demod(yy) for yy in y]

    def _processChunk(self, y: np.ndarray, shift: np.ndarray) -> np.ndarray[any, np.dtype[np.real]]:
        y = self.correctIq(y)
        if shift is not None:
            y = y * shift
        if self._decimationFactor > 1:
            y = signal.decimate(y, self._decimationFactor, ftype=self._aaFilter)
        y = self._demod(y)
        return applyFilters(y, self._outputFilters)

    def _bufferChunk(self, isDead: Value, buffer: Queue, Y: np.ndarray, shift: np.ndarray):
        for i in self._ii:
            y = buffer.get()
            if y is None or not len(y):
                isDead.value = 1
                break
            if Y is None:
                Y = np.ndarray(shape=(self._nCpus, y.size), dtype=np.complex128)
            if shift is None:
                shift = self._generateShift(self._nCpus, y.size)
            if len(y) < Y.shape[1]:
                y = np.pad(y, (0, -len(y) + Y.shape[1]), mode='constant', constant_values=0)
            Y[i] = y
        return Y, shift, self._processChunk(Y, shift)

    def __processData(self, isDead: Value, buffer: Queue, file):
        Y = None
        shift = None

        while not isDead.value:
            Y, shift, y = self._bufferChunk(isDead, buffer, Y, shift)
            size = y.size
            y = y.flat
            if self.smooth:
                y = signal.savgol_filter(y, self.smooth, self._FILTER_DEGREE)
            file.write(struct.pack('@' + (size * 'd'), *y))

    def _generateShift(self, r: int, c: int) -> np.ndarray | None:
        if self.centerFreq:
            return np.broadcast_to(np.exp(-2j * np.pi * (self.centerFreq / self.__fs) * np.arange(c)), (r, c))
        else:
            return None

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
                buffer.cancel_join_thread()
                vprint(f'Standard writer halted')
                return

    def __repr__(self):
        d = {key: value for key, value in self.__dict__.items()
             if not key.startswith('_')
             and not callable(value)
             and not issubclass(type(value), np.ndarray)
             and not issubclass(type(value), signal.dlti)
             and not issubclass(type(value), IQCorrection)
             and key not in {'outputFilters'}}
        d['fs'] = self.__fs
        d['decimatedFs'] = self.__decimatedFs
        return json.dumps(d, indent=2)
