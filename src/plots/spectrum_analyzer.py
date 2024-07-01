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
from misc.general_util import printException
from plots.abstract_plot import AbstractPlot


class SpectrumAnalyzer(DataProcessor, AbstractPlot, ABC):

    def __init__(self,
                 buffer: Queue,
                 nfft: int = 2048,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        import pyqtgraph as pg
        from pyqtgraph.Qt import QtCore, QtWidgets

        self.nfft = nfft

        self.buffer = buffer
        self.app = QtWidgets.QApplication([])
        self.window = QtWidgets.QMainWindow()
        self.centralWidget = QtWidgets.QWidget()
        self.widget = pg.PlotWidget(show=True)
        self.widgets = [(self.widget, 0)]
        self.item = self.widget.getPlotItem()

        self.item.setXRange(-self.nyquistFs, self.nyquistFs, padding=0)
        self.app.quitOnLastWindowClosed()
        self.window.setWindowTitle("SpectrumAnalyzer")
        self.window.resize(800, 600)
        self.window.setCentralWidget(self.centralWidget)
        self.layout = QtWidgets.QGridLayout()
        self.centralWidget.setLayout(self.layout)
        self.item.setMouseEnabled(x=False, y=False)
        self.item.setYRange(-6, 4)
        self.item.setMenuEnabled(False)
        self.item.showAxes(True, showValues=(False, False, False, True))
        self.item.hideButtons()
        self.axis = self.item.getAxis("bottom")
        self.axis.setLabel("Frequency [MHz]")
        self.lines = [self.item.plot()]
        self.layout.addWidget(self.widget, 0, 0)
        self.ticks = None
        self.window.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frameRate)

    def update(self):
        try:
            length, data = self.receiveData()
            if data is None or not length:
                raise KeyboardInterrupt

            amps = fft.fftn(data, norm='forward')
            # amps = signal.decimate(amps, amps.size // self.nfft)
            amps = np.abs(fft.fftshift(amps))
            amps = np.log10(amps * amps)
            freq = fft.fftshift(fft.fftfreq(amps.size, self.dt))

            if self.ticks is None:
                for widget, offset in self.widgets:
                    xr, yr = widget.viewRange()
                    if xr[0] != -0.5 and xr[1] != 0.5:
                        self.ticks = self._setTicks(widget.getAxis('bottom'), xr,
                                                    (-self.nyquistFs, self.nyquistFs), 11,
                                                    lambda v: str(round((v + self.tuned + offset) / 10E+5, 3)))

            for line in self.lines:
                line.setData(freq, amps)

        except (ValueError, KeyboardInterrupt):
            self.quit()
        except Exception as e:
            printException(e)
            self.quit()

    @abstractmethod
    def receiveData(self) -> tuple[int, any]:
        pass

    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        from pyqtgraph.Qt import QtWidgets
        cls.spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
        QtWidgets.QApplication.instance().exec()

    def quit(self):
        self.timer.stop()
        self.buffer.close()
        self.buffer.join_thread()
        super().quit()
