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

import numpy as np

from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from plots.spectrum_analyzer import SpectrumAnalyzer


class SpectrumAnalyzerPlot(SpectrumAnalyzer):
    def __init__(self,
                 correctIq: bool = False,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.iqCorrector = IQCorrection(self.fs) if correctIq else None
        self._setTicks(self.nyquistFs)

    def receiveData(self) -> tuple[int, np.ndarray]:
        data = self.buffer.get()
        length = len(data)
        if self.iqCorrector is not None:
            data = self.iqCorrector.correctIq(data)
        return length, shiftFreq(data, self.offset, self.fs)
