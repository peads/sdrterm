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
from multiprocessing import Queue, Value
from uuid import uuid4

from dsp.data_processor import DataProcessor
from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from misc.general_util import tprint, eprint
from plots.spectrum_analyzer import SpectrumAnalyzer


class SpectrumAnalyzerPlot(DataProcessor, SpectrumAnalyzer):
    uuid = None

    def __init__(self,
                 buffer: Queue,
                 iq: bool = False,
                 isDead: Value = None,
                 offset: int = 0,
                 **kwargs):
        kwargs['frameRate'] = 0  # the framerate is (likely network-)IO-bound
        super().__init__(**kwargs)
        self.buffer = buffer
        self.isDead = isDead
        self.offset = offset
        self.uuid = uuid4()
        self.iqCorrector = IQCorrection(self.fs) if iq else None

    def __del__(self):
        self.buffer.close()
        self.buffer.cancel_join_thread()

    def receiveData(self):
        data = self.buffer.get()
        data = data[:self.nfft]
        if self.iqCorrector is not None:
            data = self.iqCorrector.correctIq(data)
        return shiftFreq(data, self.offset, self.fs)

    @classmethod
    def processData(cls, isDead, buffer, fs, **kwargs):
        cls.start(fs, buffer=buffer, isDead=isDead, **kwargs)

    def update(self):
        from pyqtgraph.Qt.QtCore import QCoreApplication
        if not self.isDead.value:
            super().update()
        else:
            tprint(f'Closing buffer {self.buffer}-{type(self).__name__}-{self.uuid}')
            self.buffer.close()
            self.buffer.cancel_join_thread()
            tprint(f'Closed buffer {self.buffer}-{type(self).__name__}-{self.uuid}')
            tprint(f'Quitting {type(self).__name__}-{self.uuid}')
            QCoreApplication.quit()
            eprint(f'Plot {type(self).__name__}-{self.uuid} halted')
