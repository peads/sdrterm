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
from abc import abstractmethod, ABC
from multiprocessing import Value, Queue

import numpy as np
from scipy import fft

from dsp.data_processor import DataProcessor
from misc.general_util import printException, tprint
from plots.plot_interface import PlotInterface


class SpectrumAnalyzer(DataProcessor, PlotInterface, ABC):

    # frameRate default: ~60 fps
    def __init__(self,
                 fs: int,
                 nfft: int = 2048,
                 frameRate=17,
                 isDead: Value = None,
                 **kwargs):

        self.freq = None
        self.amps = None
        self.fftData = None
        self.isDead = isDead
        import pyqtgraph as pg
        from pyqtgraph.Qt import QtCore, QtWidgets

        self.app = QtWidgets.QApplication([])
        self.window = QtWidgets.QMainWindow()
        self.centralWidget = QtWidgets.QWidget()
        self.widget = pg.PlotWidget(name="spectrum")
        self.item = self.widget.getPlotItem()
        self.fs = fs
        self.length = self.chunk = self.nfft = nfft

        self.item.setXRange(-self._nyquistFs, self._nyquistFs, padding=0)
        self.app.quitOnLastWindowClosed()
        self.window.setWindowTitle("SpectrumAnalyzer")
        self.window.resize(800, 600)
        self.window.setCentralWidget(self.centralWidget)
        self.layout = QtWidgets.QGridLayout()
        self.centralWidget.setLayout(self.layout)
        self.item.setMouseEnabled(x=False, y=False)
        self.item.setYRange(-6, 4)
        self.axis = self.item.getAxis("bottom")
        self.axis.setLabel("Frequency [Hz]")
        self.line = self.item.plot()
        self.layout.addWidget(self.widget, 0, 0)
        self.window.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(frameRate)

    def update(self):
        try:
            data = self.receiveData()
            if data is None or not self.length or self.isDead.value:
                raise KeyboardInterrupt
            data = np.reshape(data, (self.length // self.nfft, self.nfft))

            self.fftData = fft.fftshift(fft.fftn(data, norm='forward'))
            self.amps = np.abs(self.fftData)
            self.amps = np.log10(self.amps * self.amps)
            self.freq = fft.fftshift(fft.fftfreq(self.nfft, self._inverseFs))

            for amp in self.amps:
                if self.line is not None:
                    self.line.setData(self.freq, amp)
        except (ValueError, KeyboardInterrupt):
            tprint(f'Quitting {type(self).__name__}...')
            self.quit()
        except Exception as e:
            tprint(f'Quitting {type(self).__name__}...')
            printException(e)
            self.quit()

    @abstractmethod
    def receiveData(self):
        pass

    # @classmethod
    # def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
    #     cls.start(fs, buffer=buffer, isDead=isDead, *args, **kwargs)
    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        from pyqtgraph.Qt import QtWidgets
        cls.spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
        QtWidgets.QApplication.instance().exec()

    @property
    def fs(self) -> int:
        return self._fs

    @fs.setter
    def fs(self, value: int) -> None:
        self._fs = value
        self._inverseFs = 1 / value
        self._nyquistFs = value >> 1
        self.item.setXRange(-self._nyquistFs, self._nyquistFs, padding=0)

    @fs.deleter
    def fs(self) -> None:
        del self._fs
        del self._inverseFs
        del self._nyquistFs
