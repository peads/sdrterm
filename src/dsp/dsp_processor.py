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
from typing import Callable

import numpy as np
from scipy import signal

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod
from dsp.iq_correction import IQCorrection
from dsp.util import applyFilters, generateBroadcastOutputFilter, generateFmOutputFilters, shiftFreq
from misc.general_util import deinterleave, printException, vprint, eprint, initializer


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

    def demod(self, y: np.ndarray[any, np.complex64 | np.complex128]) -> np.ndarray[any, np.real]:
        pass

    def setDemod(self, fun: Callable[[np.ndarray[any, np.complex64 | np.complex128]], np.ndarray[any, np.real]]) -> \
                Callable[[np.ndarray[any, np.complex64 | np.complex128]], np.ndarray[any, np.real]]:
        if fun is not None:
            setattr(self, 'demod', fun)
            self.sosIn = signal.ellip(self._FILTER_DEGREE, 1, 30, [1, self.bandwidth >> 1],
                                      btype='bandpass',
                                      analog=False,
                                      output='sos',
                                      fs=self.__decimatedFs)
            return self.demod
        raise ValueError("Demodulation function is not defined")

    def selectOuputFm(self):
        vprint('NFM Selected')
        self.bandwidth = 12500
        self.outputFilters = [signal.ellip(self._FILTER_DEGREE, 1, 30, self.omegaOut,
                                           btype='lowpass',
                                           analog=False,
                                           output='sos',
                                           fs=self.__decimatedFs)]
        self.setDemod(fmDemod)

    def selectOuputWfm(self):
        vprint('WFM Selected')
        self.bandwidth = 15000
        self.outputFilters = generateFmOutputFilters(self.__decimatedFs, self._FILTER_DEGREE,
                                                     18000)
        self.setDemod(fmDemod)

    def selectOuputAm(self):
        vprint('AM Selected')
        self.bandwidth = 10000
        self.outputFilters = [
            generateBroadcastOutputFilter(self.__decimatedFs, self._FILTER_DEGREE)]
        self.setDemod(amDemod)

    def processChunk(self, y: list) -> np.ndarray[any, np.real] | None:
        if y is None or not len(y):
            raise ValueError('Empty chunk')

        y = deinterleave(y)

        if self.correctIq is not None:
            y = self.correctIq.correctIq(y)

        y = shiftFreq(y, self.centerFreq, self.__fs)

        if self._decimationFactor > 1:
            y = signal.decimate(y, self._decimationFactor, ftype='fir')

        y = signal.sosfilt(self.sosIn, y)
        y = self.demod(y)
        y = applyFilters(y, self.outputFilters)

        return y

    def __processMultithreaded(self, isDead: Value, buffer: Queue, file):
        vprint('Processing multithreaded')
        n = os.cpu_count() >> 1
        if n < 2:
            raise RuntimeError('CPU count must be at least 4')
        vprint(f'Processing on {n} threads')
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

                y = pool.map_async(self.processChunk, data)
                y = list(itertools.chain.from_iterable(y.get()))
                if self.smooth:
                    y = signal.savgol_filter(y, 14, self._FILTER_DEGREE)
                file.write(struct.pack('=' + (len(y) * 'd'), *y))
                data.clear()

    def __processData(self, isDead: Value, buffer: Queue, file):
        vprint('Processing on single-thread')
        while not isDead.value:
            y = self.processChunk(buffer.get())
            if y is None or not len(y):
                isDead.value = 1
                break
            file.write(struct.pack('=' + (len(y) * 'd'), *y))

    def processData(self, isDead: Value, buffer: Queue, f: str) -> None:
        with open(f, 'wb') if f is not None else open(sys.stdout.fileno(), 'wb', closefd=False) as file:
            try:
                if self.multiThreaded:
                    self.__processMultithreaded(isDead, buffer, file)
                else:
                    self.__processData(isDead, buffer, file)
                file.write(b'')
            except (ValueError, KeyboardInterrupt):
                pass
            except Exception as e:
                eprint(f'Process {multiprocessing.current_process().name} raised exception')
                printException(e)
            finally:
                isDead.value = 1
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
