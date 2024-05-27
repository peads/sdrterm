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
import os
import struct
import sys
from functools import partial
from multiprocessing import Pool, Value, Pipe
from typing import Callable

import numpy as np
from scipy import signal

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod, realOutput
from dsp.iq_correction import IQCorrection
from dsp.util import applyFilters, generateBroadcastOutputFilter, generateFmOutputFilters, shiftFreq
from misc.general_util import applyIgnoreException, deinterleave, printException, tprint, \
    vprint, initializer


def handleException(isDead, e):
    isDead.value = 1
    if not isinstance(e, KeyboardInterrupt):
        printException(e)


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
                 demod: Callable[[np.ndarray[any, np.complex_]], np.ndarray] = realOutput,
                 **_):

        # decimation = decimation if decimation is not None else 2
        self.outputFilters = []
        self.sosIn = None
        self.__decimatedFs = self.__fs = fs
        self.__decimationFactor = decimation
        self.__decimatedFs //= decimation
        self.centerFreq = centerFreq
        self.demod = demod
        self.bandwidth = None
        self.tunedFreq = tunedFreq
        self.vfos = vfos
        self.omegaOut = omegaOut
        self.correctIq = IQCorrection(self.__decimatedFs) if correctIq else None

    @property
    def fs(self):
        return self.__fs

    @fs.setter
    def fs(self, fs):
        self.__fs = fs
        self.__decimatedFs = fs // self.__decimationFactor

    @fs.deleter
    def fs(self):
        del self.__fs

    @property
    def decimation(self):
        return self.__decimationFactor

    @decimation.deleter
    def decimation(self):
        del self.__decimationFactor

    @decimation.setter
    def decimation(self, decimation):
        if not decimation or decimation < 2:
            raise ValueError("Decimation must be at least 2.")
        self.__decimationFactor = decimation
        self.__decimatedFs = self.__fs // decimation
        self.correctIq = IQCorrection(self.__decimatedFs) if self.correctIq else None

    @property
    def decimatedFs(self):
        return self.__decimatedFs

    @decimatedFs.deleter
    def decimatedFs(self):
        del self.__decimatedFs

    def setDemod(self, fun):
        if bool(fun):
            self.demod = fun
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
        try:
            y = deinterleave(y)

            if self.correctIq is not None:
                y = self.correctIq.correctIq(y)

            y = shiftFreq(y, self.centerFreq, self.__fs)

            if self.__decimationFactor > 1:
                y = signal.decimate(y, self.__decimationFactor, ftype='fir')

            y = signal.sosfilt(self.sosIn, y)
            y = self.demod(y)
            y = applyFilters(y, self.outputFilters)

            return y
        except KeyboardInterrupt:
            return None

    def processData(self, isDead: Value, pipe: Pipe, f) -> None:
        reader, writer = pipe

        data = []
        try:
            with open(f, 'wb') if f is not None else open(sys.stdout.fileno(), 'wb',
                                                          closefd=False) as file:
                tprint(f'{f} {file}')
                with Pool(initializer=initializer, initargs=(isDead,)) as pool:
                    ii = range(os.cpu_count())
                    while not isDead.value:
                        for _ in ii:
                            y = reader.recv()
                            if y is None or not len(y):
                                break
                            data.append(y)

                        if data is None or not len(data):
                            break

                        y = pool.map_async(self.processChunk, data)
                        y = list(itertools.chain.from_iterable(y.get()))
                        y = signal.savgol_filter(y, 14, self._FILTER_DEGREE)
                        file.write(struct.pack(len(y) * 'd', *y))
                        data.clear()
                    pool.close()
                    pool.join()
                del pool
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            pass
        except TypeError as e:
            if "'NoneType' object cannot be interpreted as an integer" not in str(e):
                printException(e)
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            applyIgnoreException(partial(file.write, b''))
            applyIgnoreException(writer.close)
            applyIgnoreException(reader.close)
            print(f'File writer halted')

    def __repr__(self):
        d = {key: value for key, value in self.__dict__.items()
             if not key.startswith('_')
             and not callable(value)
             and not isinstance(value, np.ndarray)
             and not isinstance(value, IQCorrection)
             and key not in {'outputFilters'}}
        d['fs'] = self.fs
        d['decimatedFs'] = self.decimatedFs
        return json.dumps(d, indent=2)
