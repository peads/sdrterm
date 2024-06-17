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

from misc.general_util import deinterleave
from plots.qt_spectrum_analyzer import AbstractSpectrumAnalyzer


class SpectrumAnalyzerPlot(AbstractSpectrumAnalyzer):
    uuid = None

    def __init__(self, fs: int, iq: bool = True, buffer: Queue = None, isDead: Value = None, frameRate: int = 0):
        super().__init__(fs, iq, frameRate=frameRate)
        self.buffer = buffer
        self.isDead = isDead
        self.uuid = uuid4()

    def __del__(self):
        self.buffer.close()
        self.buffer.cancel_join_thread()

    def receiveData(self):
        return deinterleave(self.buffer.get())

    @classmethod
    def processData(cls, isDead, buffer, fs):
        cls.start(fs, buffer=buffer, isDead=isDead)

    def update(self):
        from pyqtgraph.Qt.QtCore import QCoreApplication
        if not self.isDead.value:
            super().update()
        else:
            QCoreApplication.quit()
