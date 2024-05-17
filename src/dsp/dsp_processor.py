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
import struct

import numpy as np
from scipy import signal

from dsp.data_processor import DataProcessor
from dsp.demodulation import amDemod, fmDemod, realDemod
from dsp.util import applyFilters, cnormalize, convertDeinterlRealToComplex, generateAmInputFilters, \
    generateBroadcastOutputFilter, generateFmInputFilters, generateFmOutputFilters, shiftFreq
from misc.general_util import deinterleave, eprint, printException


class DspProcessor(DataProcessor):
    def __init__(self,
                 fs: str,
                 decimation: str,
                 centerFreq: str,
                 omegaOut: int,
                 demod: str = None,
                 tunedFreq: str = None,
                 vfos: str = None,
                 normalize: bool = False):
        try:
            fs = int(fs)
            centerFreq = float(centerFreq)
            tunedFreq = float(tunedFreq) if tunedFreq is not None else None
            decimation = int(decimation) if decimation is not None else 1
        except (ValueError, TypeError) as e:
            raise ValueError(e)

        self._FILTER_DEGREE = 8
        self.outputFilters = []
        self.sosIn = None
        self.fs = fs
        self.decimationFactor = decimation if decimation is not None and decimation > 0 else (
                    np.floor(np.log2(fs / 1000)) - 8)
        self.logDecimationFactor = self.decimationFactor
        self.decimatedFs = fs >> int(
            np.round(self.decimationFactor)) if self.decimationFactor > 0 else fs
        self.decimationFactor = 1 << int(np.round(self.decimationFactor))
        self.isRunning = True
        self.centerFreq = centerFreq
        self.demod = demod if demod is not None else realDemod
        self.bandwidth = None
        self.tunedFreq = tunedFreq
        self.vfos = [float(x) for x in vfos.split(',')] if not (
                    vfos is None or len(vfos) < 1) else None
        self.normalize = normalize
        self.omegaOut = omegaOut
        eprint(
            f'input sample rate: {self.fs} decimation factor {self.decimationFactor} '
            f'decimated sample rate {self.decimatedFs} center frequency: {self.centerFreq} '
            f'tuned frequency: {self.tunedFreq} vfo offsets: {self.vfos}')

    def setDecimation(self, decimation):
        if decimation is not None:
            self.decimationFactor = decimation
        else:
            self.decimationFactor = np.floor(np.log2(self.fs / 1000)) - 8

        self.decimationFactor = int(np.round(self.decimationFactor))
        self.logDecimationFactor = self.decimationFactor
        self.decimatedFs = self.fs >> self.logDecimationFactor if self.logDecimationFactor > 0 else self.fs
        self.decimationFactor = 1 << self.logDecimationFactor

    def setDemod(self, fun):
        if bool(fun):
            self.demod = fun
            return self.demod
        raise ValueError("Demodulation function is not defined")

    def selectOuputFm(self):
        eprint('NFM Selected')
        self.bandwidth = 12500
        self.sosIn = generateFmInputFilters(self.decimatedFs, self._FILTER_DEGREE, self.bandwidth)
        self.outputFilters = [signal.butter(self._FILTER_DEGREE, self.omegaOut,
                                            btype='lowpass',
                                            analog=False,
                                            output='sos',
                                            fs=self.decimatedFs >> 1)]
        self.setDemod(fmDemod)

    def selectOuputWfm(self):
        eprint('WFM Selected')
        self.bandwidth = 15000
        self.sosIn = generateFmInputFilters(self.decimatedFs, self._FILTER_DEGREE, self.bandwidth)
        self.outputFilters = generateFmOutputFilters(self.decimatedFs >> 1, self._FILTER_DEGREE,
                                                     18000)
        self.setDemod(fmDemod)

    def selectOuputAm(self):
        eprint('AM Selected')
        self.bandwidth = 10000
        self.sosIn = generateAmInputFilters(self.decimatedFs, self._FILTER_DEGREE, self.bandwidth)
        self.outputFilters = [generateBroadcastOutputFilter(self.decimatedFs, self._FILTER_DEGREE)]
        self.setDemod(amDemod)

    def processData(self, isDead, pipe, f) -> None:
        if f is None or (isinstance(f, str)) and len(f) < 1:
            raise ValueError('f is not defined')
        reader, writer = pipe
        normalize = cnormalize if self.normalize else lambda x: x
        with open(f, 'wb') as file:
            try:
                while not isDead.value:
                    writer.close()
                    y = reader.recv()
                    y = deinterleave(y)
                    y = convertDeinterlRealToComplex(y)
                    y = normalize(y)
                    y = shiftFreq(y, self.centerFreq, self.fs)
                    y = signal.decimate(y, self.decimationFactor, ftype='fir')
                    y = signal.sosfilt(self.sosIn, y)
                    y = self.demod(y)
                    y = applyFilters(y, self.outputFilters)
                    file.write(struct.pack(len(y) * 'd', *y))
            except (EOFError, KeyboardInterrupt):
                pass
            except Exception as e:
                printException(e)
            finally:
                file.write(b'')
                reader.close()
                eprint(f'File writer halted')
