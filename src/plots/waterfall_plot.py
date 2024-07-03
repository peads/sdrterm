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

from numpy import log10, abs, zeros, float64
from scipy.signal import ShortTimeFFT

from dsp.data_processor import DataProcessor
from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from misc.general_util import printException
from plots.abstract_plot import AbstractPlot


class WaterfallPlot(DataProcessor, AbstractPlot):
    NPERSEG = 256
    NOOVERLAP = NPERSEG >> 1
    NFFT = 1024

    def __init__(self,
                 buffer: Queue,
                 correctIq: bool = False,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        from pyqtgraph import ImageItem, PlotWidget, colormap
        from pyqtgraph.Qt.QtCore import QTimer
        from pyqtgraph.Qt.QtWidgets import QMainWindow, QApplication
        from pyqtgraph.Qt.QtGui import QTransform
        self.buffer = buffer
        self.iqCorrector = IQCorrection(self.fs) if correctIq else None
        self._SFT = ShortTimeFFT.from_window(('kaiser', 5),
                                             self.fs,
                                             self.NPERSEG,
                                             self.NOOVERLAP,
                                             mfft=self.NFFT,
                                             fft_mode='centered',
                                             scale_to='magnitude',
                                             phase_shift=None)
        self.pad_extent = (self.NFFT - self.NOOVERLAP) / (self.fs << 1)

        self.app = QApplication([])
        self.window = QMainWindow()
        self.item = ImageItem()
        self.widget = PlotWidget()
        self.plot = self.widget.plotItem
        self.axis = self.plot.getAxis("bottom")
        self.xscale = self.NFFT / self.fs
        self.image = zeros((self.NFFT, self.NPERSEG + 1), dtype=float64)

        self.window.setCentralWidget(self.widget)
        self.plot.addItem(self.item)
        self.window.setWindowTitle("Waterfall")
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        self.plot.showAxes(True, showValues=(False, False, False, True))#, size=(self.NFFT, self.NOOVERLAP >> 1))
        self.item.setLevels(None)
        self.axis.setLabel("Frequency", units="Hz", unitPrefix="M")

        transform = QTransform.fromScale(self.fs * self.xscale, 1)
        transform = transform.translate(-self.nyquistFs * self.xscale, 0)
        self.item.setTransform(transform)

        colorMap = colormap.get('CET-CBL2')
        lut = colorMap.getLookupTable(nPts=256)
        bwLevels = [-16, 16]
        self.item.setLookupTable(lut)
        self.item.setLevels(bwLevels)
        self.item.setImage(self.image, autoLevels=False)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frameRate)
        self.receiveData = self.buffer.get
        if self.iqCorrector is not None:
            self.correctIq = self.iqCorrector.correctIq

    def correctIq(self, y):
        return y

    def quit(self):
        self.timer.stop()
        self.buffer.close()
        self.buffer.join_thread()
        super().quit()

    def receiveData(self):
        return None

    def update(self):
        try:
            self.image[:] = 10. * log10(abs(self._SFT.stft(shiftFreq(self.correctIq(self.receiveData()), self.offset, self.fs))))
            self.item.setImage(autoLevels=False)
        except KeyboardInterrupt:
            self.quit()
        except Exception as e:
            if "object has no attribute 'shape'" not in str(e):
                printException(e)
            self.quit()

    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        try:
            from pyqtgraph.Qt import QtWidgets
            spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
            spec.window.show()
            QtWidgets.QApplication.instance().exec()
        except KeyboardInterrupt:
            pass
