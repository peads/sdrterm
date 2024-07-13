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

from numpy import log10, abs, zeros, float64
from scipy.signal import ShortTimeFFT

from dsp.iq_correction import IQCorrection
from misc.general_util import printException
from plots.abstract_plot import AbstractPlot


class WaterfallPlot(AbstractPlot):
    _NPERSEG: int = 256
    _NOOVERLAP: int = _NPERSEG >> 1
    _NFFT: int = 1024

    def __init__(self,
                 correctIq=False,
                 fileInfo=None,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

        from pyqtgraph import ImageItem, PlotWidget, colormap
        from pyqtgraph.Qt.QtCore import QTimer
        from pyqtgraph.Qt.QtWidgets import QMainWindow, QApplication
        from pyqtgraph.Qt.QtGui import QTransform

        COLOR_MAP = colormap.get('CET-CBL2')
        LUT = COLOR_MAP.getLookupTable(nPts=256)
        BW_LEVELS = (-32, 32)

        self.image = None
        self.size = 0
        self._SFT = ShortTimeFFT.from_window(('kaiser', 5),
                                             self.fs,
                                             self._NPERSEG,
                                             self._NOOVERLAP,
                                             mfft=self._NFFT,
                                             fft_mode='centered',
                                             scale_to='magnitude',
                                             phase_shift=None)
        self._padExtent = (self._NFFT - self._NOOVERLAP) / (self.fs << 1)

        self.app = QApplication([])
        self.window = QMainWindow()
        self.item = ImageItem()
        self.widget = PlotWidget()
        self.plot = self.widget.plotItem
        self.axis = self.plot.getAxis("bottom")

        self.window.setCentralWidget(self.widget)
        self.plot.addItem(self.item)
        self.window.setWindowTitle("Waterfall")
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        self.plot.showAxes(True, showValues=(False, False, False, True))
        self.item.setLevels(None)

        transform = QTransform.fromScale(self._NFFT, 1)
        transform = transform.translate(-(self._NFFT >> 1), 0)  # + self.tuned / self._NFFT, 0)
        self.item.setTransform(transform)
        self.item.setLookupTable(LUT)
        self.item.setLevels(BW_LEVELS)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frameRate)
        if not correctIq and fileInfo['bitsPerSample'].char.isupper():
            setattr(self, '_doCorrectIq', IQCorrection(self.fs).correctIq)

    def _doCorrectIq(self, _) -> None:
        pass

    def update(self):
        try:
            length = self.receiveData()
            if self.image is None or length != self.size:
                col = len(self._y) // self._NOOVERLAP
                self.image = zeros((self._NFFT, col + 1), dtype=float64)
                self.item.setImage(self.image, autoLevels=False)
                self.size = length
            self._doCorrectIq(self._y)
            self._shiftFreq(self._y)
            self.image[:] = 10. * log10(abs(self._SFT.stft(self._y)))
            self.item.setImage(autoLevels=False)
        except (RuntimeWarning, ValueError, KeyboardInterrupt):
            self.quit()
        except Exception as e:
            printException(e)
            self.quit()
