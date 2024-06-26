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

import numpy as np
from scipy.signal import ShortTimeFFT

from dsp.data_processor import DataProcessor
from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from misc.general_util import tprint
from plots.plot_interface import PlotInterface


class WaterfallPlot(DataProcessor, PlotInterface):
    NPERSEG = 1024
    NOOVERLAP = NPERSEG >> 1
    NFFT = NPERSEG

    def __init__(self,
                 fs: int,
                 buffer: Queue,
                 isDead: Value,
                 correctIq: bool = False,
                 nfft: int = 2048,
                 frameRate=17,
                 center: int = 0,
                 *args,
                 **kwargs):
        import pyqtgraph as pg
        from pyqtgraph.Qt import QtWidgets, QtCore
        self.fs = fs
        self.nfft = nfft
        self.frameRate = frameRate
        self.buffer = buffer
        self.isDead = isDead
        self.dt = 1 / self.fs
        self.offset = center
        self.iqCorrector = IQCorrection(self.fs) if correctIq else None
        self._SFT = ShortTimeFFT.from_window(('kaiser', 5),
                                             self.fs,
                                             self.NPERSEG,
                                             self.NOOVERLAP,
                                             mfft=self.NFFT,
                                             fft_mode='centered',
                                             scale_to='magnitude',
                                             phase_shift=None)
        self.pad_xextent = (self.NFFT - self.NOOVERLAP) / (self.fs * 2)

        self.app = QtWidgets.QApplication([])
        self.window = QtWidgets.QMainWindow()
        self.centralWidget = QtWidgets.QWidget()
        self.widget = pg.GraphicsLayoutWidget(show=True)
        self.layout = QtWidgets.QVBoxLayout()
        self.centralWidget.setLayout(self.layout)

        self.surf = self.widget.addPlot(title="non-interactive")
        self.item = pg.ImageItem(colorMap='CET-CBL2')
        self.surf.addItem(self.item)
        self.surf.setMouseEnabled(x=False, y=False)
        self.surf.hideButtons()
        self.surf.showAxes(True, showValues=(True, False, False, True))
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(frameRate)

    def receiveData(self):
        data = self.buffer.get()
        if self.iqCorrector is not None:
            data = self.iqCorrector.correctIq(data)
        return shiftFreq(data, self.offset, self.fs)

    def update(self):
        try:
            y = self.receiveData()
            if y is None or not len(y) or self.isDead.value:
                raise KeyboardInterrupt
            Zxx = self._SFT.stft(y)
            # extent = xmin, xmax, fmin, fmax = self._SFT.extent(len(y), center_bins=True)
            # xmin -= self.pad_xextent
            # xmax += self.pad_xextent

            data = 10. * np.log10(np.abs(Zxx))
            self.item.setImage(data)
        except KeyboardInterrupt:
            tprint(f'Quitting {type(self).__name__}...')
            self.quit()
        except Exception as e:
            tprint(f'Quitting {type(self).__name__}...')
            self.quit()

    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        from pyqtgraph.Qt import QtWidgets
        cls.spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
        QtWidgets.QApplication.instance().exec()
