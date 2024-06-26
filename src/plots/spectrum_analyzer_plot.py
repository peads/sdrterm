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
from multiprocessing import Queue

from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from plots.spectrum_analyzer import SpectrumAnalyzer


class SpectrumAnalyzerPlot(SpectrumAnalyzer):
    def __init__(self,
                 buffer: Queue,
                 correctIq: bool = False,
                 center: int = 0,
                 **kwargs):
        # kwargs['frameRate'] = 0  # the framerate is (likely network-)IO-bound
        super().__init__(**kwargs)
        self.buffer = buffer
        self.offset = center
        self.iqCorrector = IQCorrection(self.fs) if correctIq else None

    def __del__(self):
        self.buffer.close()
        self.buffer.cancel_join_thread()
        self.quit()

    def receiveData(self):
        data = self.buffer.get()
        self.length = len(data)
        # if self.length != self.nfft * (self.length // self.nfft):
        #     data = data[:1 << int(np.log2(self.length))]
        if self.iqCorrector is not None:
            data = self.iqCorrector.correctIq(data)
        return shiftFreq(data, self.offset, self.fs)
