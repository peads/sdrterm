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


class _EmptyChunkError(ValueError):
    def __init__(self):
        super().__init__('Empty chunk')


class DspProcessor(DataProcessor):
    _FILTER_DEGREE = 2

    def __init__(self,
                 fs: int,
                 centerFreq: float,
                 omegaOut: int,
                 tunedFreq: int,
                 vfos: str,
                 correctIq: bool,
                 decimation: int,
                 smooth: bool = False,
                 cpus: int = 0,
                 **kwargs):

        self.bandwidth \
            = self.__fs \
            = self.__dt \
            = self.__decimatedFs \
            = self.__decDt \
            = self._aaFilter = None
        self._outputFilters = []
        self._decimationFactor = decimation
        self.fs = fs
        self.centerFreq = centerFreq
        self.tunedFreq = tunedFreq
        self.vfos = vfos
        self.omegaOut = omegaOut
        if correctIq:
            setattr(self, 'correctIq', IQCorrection(self.__decimatedFs).correctIq)
        self.smooth = smooth

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

    @property
    def inverseDfs(self):
        return self.__decDt

    @inverseDfs.setter
    def inverseDfs(self, _):
        raise NotImplementedError('Setting the inverseDfs directly is not supported. Set fs instead')

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
            self._aaFilter = signal.ellip(self._FILTER_DEGREE << 1, 1, 30,
                                          Wn=self.bandwidth,
                                          btype='lowpass',
                                          analog=False,
                                          output='zpk',
                                          fs=self.__fs)
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

    def __processChunk(self, y: np.ndarray, shift: np.ndarray) -> np.ndarray[any, np.dtype[np.real]]:
        y = self.correctIq(y)
        if shift is not None:
            y = y * shift
        if self._decimationFactor > 1:
            y = signal.decimate(y, self._decimationFactor, ftype=self._aaFilter)
        y = [self.demod(yy) for yy in y]
        return applyFilters(y, self._outputFilters)

    def __processData(self, isDead: Value, buffer: Queue, file):
        vprint('Processing on single-thread')
        nCpus = os.cpu_count()
        ii = range(nCpus)
        Y = None
        shift = None

        def generateShift(r: int, c: int):
            if self.centerFreq:
                return np.broadcast_to(np.exp(-2j * np.pi * (self.centerFreq / self.__fs) * np.arange(c)), (r, c))
            else:
                return None

        while not isDead.value:
            for i in ii:
                y = buffer.get()
                if y is None or not len(y):
                    isDead.value = 1
                    break
                if Y is None:
                    Y = np.ndarray(shape=(nCpus, y.size), dtype=np.complex128)
                if shift is None:
                    shift = generateShift(nCpus, y.size)
                Y[i] = y
            y = self.__processChunk(Y, shift)
            file.write(struct.pack('@' + (y.size * 'd'), *y.flat))

    def processData(self, isDead: Value, buffer: Queue, f: str) -> None:
        with open(f, 'wb') if f is not None else open(sys.stdout.fileno(), 'wb', closefd=False) as file:
            try:
                self.__processData(isDead, buffer, file)
                file.write(b'')
                file.flush()
            except (_EmptyChunkError, KeyboardInterrupt):
                pass
            except Exception as e:
                eprint(f'Process {multiprocessing.current_process().name} raised exception')
                printException(e)
            finally:
                buffer.close()
                buffer.cancel_join_thread()
                eprint(f'File writer halted')
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
