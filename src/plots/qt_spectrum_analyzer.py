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

import numpy as np
from scipy import fft


class AbstractSpectrumAnalyzer(ABC):
    def __init__(self, fs: int, *args, **kwargs):

        import pyqtgraph as pg
        from pyqtgraph.Qt import QtCore, QtWidgets

        self.app = QtWidgets.QApplication([])
        self.window = QtWidgets.QMainWindow()
        self.centralWidget = QtWidgets.QWidget()
        self.widget = pg.PlotWidget(name="spectrum")
        self.item = self.widget.getPlotItem()
        self.fs = fs

        self.item.setXRange(-self._nyquistFs, self._nyquistFs, padding=0)
        self.app.quitOnLastWindowClosed()
        self.window.setWindowTitle("SpectrumAnalyzer")
        self.window.resize(800, 600)
        self.window.setCentralWidget(self.centralWidget)
        self.layout = QtWidgets.QVBoxLayout()
        self.centralWidget.setLayout(self.layout)
        self.item.setMouseEnabled(x=False, y=False)
        self.item.setYRange(-6, 4)
        self.axis = self.item.getAxis("bottom")
        self.axis.setLabel("Frequency [Hz]")
        self.curve_spectrum = self.item.plot()
        self.layout.addWidget(self.widget)
        self.window.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        # default: ~60 fps
        frameRate = kwargs['frameRate'] if 'frameRate' in kwargs and kwargs['frameRate'] >= 0 else 17
        self.timer.start(frameRate)

    def update(self):
        from pyqtgraph.Qt.QtCore import QCoreApplication
        try:
            data = self.receiveData()
            if data is None or not len(data):
                raise KeyboardInterrupt

            fftData = fft.fft(data, norm='forward')
            fftData = fft.fftshift(fftData)
            amps = np.abs(fftData)
            amps = np.log10(amps * amps)
            freq = fft.fftfreq(len(data), self._inverseFs)
            freq = fft.fftshift(freq)
            self.curve_spectrum.setData(freq, amps)
        except KeyboardInterrupt:
            QCoreApplication.quit()

    @abstractmethod
    def receiveData(self):
        pass

    @classmethod
    def start(cls, fs, *args, **kwargs):
        from pyqtgraph.Qt import QtWidgets
        spec = cls(fs, *args, **kwargs)
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
