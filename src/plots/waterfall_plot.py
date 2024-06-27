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
from misc.general_util import tprint, printException
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
        import pyqtgraph as pg
        from pyqtgraph.Qt import QtWidgets, QtCore
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

        self.app = QtWidgets.QApplication([])
        self.window = QtWidgets.QMainWindow()
        self.centralWidget = QtWidgets.QWidget()
        self.widget = pg.GraphicsLayoutWidget(show=True)
        self.layout = QtWidgets.QVBoxLayout()
        self.centralWidget.setLayout(self.layout)

        self.window.setWindowTitle("Waterfall")
        self.surf = self.widget.addPlot()
        self.item = pg.ImageItem(colorMap='CET-CBL2')
        self.axis = self.surf.getAxis("bottom")
        self.axis.setLabel("Frequency [MHz]")
        self.surf.addItem(self.item)
        self.surf.setMouseEnabled(x=False, y=False)
        self.surf.setMenuEnabled(False)
        self.surf.hideButtons()
        self.surf.showAxes(True, showValues=(False, False, False, True))
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frameRate)
        self.ticks = None

    def quit(self):
        self.timer.stop()
        self.buffer.close()
        self.buffer.cancel_join_thread()
        super().quit()

    def receiveData(self) -> tuple[int, np.ndarray]:
        data = self.buffer.get()
        if self.iqCorrector is not None:
            data = self.iqCorrector.correctIq(data)
        return len(data), shiftFreq(data, self.offset, self.fs)

    def update(self):
        try:
            _, y = self.receiveData()
            if y is None or not len(y):
                raise KeyboardInterrupt
            Zxx = self._SFT.stft(y)
            # extent = tmin, tmax, fmin, fmax = self._SFT.extent(len(y), center_bins=True)
            # tmin -= self.pad_extent
            # tmax += self.pad_extent

            data = 10. * np.log10(np.abs(Zxx))
            if self.ticks is None:
                xr, yr = self.surf.viewRange()
                if xr[0] != -0.5 and xr[1] != 0.5:
                    # ax = self.surf.getAxis('bottom')
                    # self.ticks = [[(float(u), str(round((v + self.tuned) / 10E+5, 3)))
                    #                for u, v in zip(np.linspace(xr[0], xr[1], 11),
                    #                                np.linspace(-self.nyquistFs, self.nyquistFs, 11))]]
                    # ax.setTicks(self.ticks)
                    self.ticks = self._setTicks(self.surf.getAxis('bottom'), xr,
                                                (-self.nyquistFs, self.nyquistFs), 11,
                                                lambda v: str(round((v + self.tuned) / 10E+5, 3)))

            self.item.setImage(data)
        except KeyboardInterrupt:
            tprint(f'Quitting {type(self).__name__}...')
            self.quit()
        except Exception as e:
            tprint(f'Quitting {type(self).__name__}...')
            printException(e)
            self.quit()

    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        from pyqtgraph.Qt import QtWidgets
        cls.spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
        QtWidgets.QApplication.instance().exec()
