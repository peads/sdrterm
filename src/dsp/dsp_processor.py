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
import itertools
import json
import multiprocessing
import os
import struct
import sys
from multiprocessing import Value, Queue, Pool
from typing import Callable, BinaryIO

import numpy as np
from scipy import signal

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod
from dsp.iq_correction import IQCorrection
from dsp.util import applyFilters, generateBroadcastOutputFilter, generateFmOutputFilters, shiftFreq, \
    generateEllipFilter
from misc.general_util import printException, vprint, eprint, initializer


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
                 multiThreaded: bool = False,
                 smooth: bool = False,
                 cpu: bool = True,
                 **kwargs):

        self.outputFilters = []
        self.sosIn = None
        self.__decimatedFs = self.__fs = fs
        self._decimationFactor = decimation
        self.__decimatedFs //= decimation
        self.centerFreq = centerFreq
        self.bandwidth = None
        self.tunedFreq = tunedFreq
        self.vfos = vfos
        self.omegaOut = omegaOut
        self.correctIq = IQCorrection(self.__decimatedFs) if correctIq else None
        self.smooth = smooth
        self.multiThreaded = multiThreaded
        self.cpu = cpu

    @property
    def fs(self):
        return self.__fs

    @fs.setter
    def fs(self, fs):
        self.__fs = fs
        self.__decimatedFs = fs // self._decimationFactor

    @fs.deleter
    def fs(self):
        del self.__fs

    @property
    def decimation(self):
        return self._decimationFactor

    @decimation.deleter
    def decimation(self):
        del self._decimationFactor

    @decimation.setter
    def decimation(self, decimation):
        if not decimation or decimation < 2:
            raise ValueError("Decimation must be at least 2.")
        self._decimationFactor = decimation
        self.__decimatedFs = self.__fs // decimation
        self.correctIq = IQCorrection(self.__decimatedFs) if self.correctIq else None

    @property
    def decimatedFs(self):
        return self.__decimatedFs

    @decimatedFs.deleter
    def decimatedFs(self):
        del self.__decimatedFs

    def demod(self, y: np.ndarray[any, np.dtype[np.complex64 | np.complex128]]) -> np.ndarray[any, np.dtype[np.real]]:
        pass

    def __setDemod(self, fun: Callable[
        [np.ndarray[any, np.dtype[np.complex64 | np.complex128]]], np.ndarray[any, np.dtype[np.real]]],
                   *filters) \
            -> Callable[[np.ndarray[any, np.dtype[np.complex64 | np.complex128]]], np.ndarray[any, np.dtype[np.real]]]:
        if fun is not None and filters is not None and len(filters) > 0:
            self.outputFilters.clear()
            self.outputFilters.extend(*filters)
            setattr(self, 'demod', fun)
            self.sosIn = generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, [1, self.bandwidth >> 1],
                                             'bandpass')
            # self.sosIn = signal.ellip(self._FILTER_DEGREE, 1, 30, [1, self.bandwidth >> 1],
            #                           btype='bandpass',
            #                           analog=False,
            #                           output='sos',
            #                           fs=self.__decimatedFs)
            return self.demod
        raise ValueError("Demodulation function is not defined")

    def selectOuputFm(self):
        vprint('NFM Selected')
        self.bandwidth = 12500
        # self.outputFilters = [signal.ellip(self._FILTER_DEGREE, 1, 30, self.omegaOut,
        #                                    btype='lowpass',
        #                                    analog=False,
        #                                    output='sos',
        #                                    fs=self.__decimatedFs)]
        self.__setDemod(fmDemod, generateEllipFilter(self.__decimatedFs, self._FILTER_DEGREE, self.omegaOut, 'lowpass'))

    def selectOuputWfm(self):
        vprint('WFM Selected')
        self.bandwidth = 15000
        self.__setDemod(fmDemod, generateFmOutputFilters(self.__decimatedFs, self._FILTER_DEGREE, 18000))

    def selectOuputAm(self):
        vprint('AM Selected')
        self.bandwidth = 10000
        self.__setDemod(amDemod, generateBroadcastOutputFilter(self.__decimatedFs, self._FILTER_DEGREE))

    def processChunk(self, y: np.ndarray[any, np.dtype[np.complex64 | np.complex128]]) \
            -> np.ndarray[any, np.dtype[np.real]]:
        if y is None or not len(y):
            raise _EmptyChunkError()

        if self.correctIq is not None:
            y = self.correctIq.correctIq(y)

        y = shiftFreq(y, self.centerFreq, self.__fs)

        if self._decimationFactor > 1:
            y = signal.decimate(y, self._decimationFactor, ftype='fir')

        y = signal.sosfilt(self.sosIn, y)
        y = self.demod(y)
        y = applyFilters(y, self.outputFilters)

        return y

    def __processMultithreaded(self, isDead: Value, buffer: Queue, file: BinaryIO) -> None:
        vprint('Processing multithreaded')
        n = os.cpu_count()
        if n < 4:
            raise ValueError('CPU count must be at least 4')
        if self.cpu:
            n >>= 1
        else:
            n -= 2
        eprint(f'Processing using {n} threads')
        ii = range(n)
        with Pool(processes=n, initializer=initializer, initargs=(isDead,)) as pool:
            data = []
            while not isDead.value:
                for _ in ii:
                    temp = buffer.get()
                    if temp is None or not len(temp):
                        isDead.value = 1
                        break
                    data.append(temp)

                if data is None or not len(data):
                    break
                y = pool.map_async(self.processChunk, data)
                y = list(itertools.chain.from_iterable(y.get()))
                if self.smooth:
                    y = signal.savgol_filter(y, 14, self._FILTER_DEGREE)
                file.write(struct.pack('@' + (len(y) * 'd'), *y))
                data.clear()

    def __processData(self, isDead: Value, buffer: Queue, file):
        vprint('Processing on single-thread')
        while not isDead.value:
            y = self.processChunk(buffer.get())
            if y is None or not len(y):
                isDead.value = 1
                break
            file.write(struct.pack('@' + (len(y) * 'd'), *y))

    def processData(self, isDead: Value, buffer: Queue, f: str) -> None:
        with open(f, 'wb') if f is not None else open(sys.stdout.fileno(), 'wb', closefd=False) as file:
            try:
                if self.multiThreaded:
                    self.__processMultithreaded(isDead, buffer, file)
                else:
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
             and not issubclass(type(value), IQCorrection)
             and key not in {'outputFilters'}}
        d['fs'] = self.fs
        d['decimatedFs'] = self.decimatedFs
        return json.dumps(d, indent=2)
