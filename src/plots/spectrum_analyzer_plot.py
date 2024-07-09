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

from numpy import log10, abs
from scipy.fft import fftshift, fftn, fftfreq

from misc.general_util import printException
from plots.abstract_plot import AbstractPlot


class SpectrumAnalyzerPlot(AbstractPlot):
    _AXES = (True, False, False, True)
    _AXES_VALUES = (False, False, False, True)

    def __init__(self,
                 nfft: int = 2048,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        from pyqtgraph import PlotWidget, GraphicsLayoutWidget
        from pyqtgraph.Qt import QtCore, QtWidgets

        self.app = QtWidgets.QApplication([])
        self.app.quitOnLastWindowClosed()

        self.window = QtWidgets.QMainWindow()
        self.layout = QtWidgets.QGridLayout()
        self.centralWidget = GraphicsLayoutWidget()
        self.widget = PlotWidget()
        self.item = self.widget.getPlotItem()
        self.axis = self.item.getAxis("bottom")
        self.plot = self.item.plot()
        self.plots = [self.plot]

        self.nfft = nfft
        self.amp = None
        self.freq = None
        self.isFirst = True

        self.centralWidget.setLayout(self.layout)
        self.window.setCentralWidget(self.centralWidget)
        self.layout.addWidget(self.widget, 0, 0)

        self.window.setWindowTitle("SpectrumAnalyzer")

        self.item.setXRange(-self.nyquistFs, self.nyquistFs, padding=0)
        self.item.setMouseEnabled(x=False, y=False)
        self.item.setYRange(-10, 10, padding=0)
        self.item.setMenuEnabled(False)
        self.item.showAxes(self._AXES, showValues=self._AXES_VALUES)
        self.item.hideButtons()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(self.frameRate)

    def update(self):
        try:
            self.receiveData()
            self._shiftFreq(self._y)
            if self.amp is None:
                self.amp = abs(fftshift(fftn(self._y, norm='forward')))
            else:
                self.amp[:] = abs(fftshift(fftn(self._y, norm='forward')))
            self.amp[:] = log10(self.amp * self.amp)

            if self.freq is None:
                self.freq = fftshift(fftfreq(self.amp.size, self.dt))
            else:
                self.freq[:] = fftshift(fftfreq(self.amp.size, self.dt))

            for plot in self.plots:
                plot.setData(self.freq, self.amp)

        except (RuntimeWarning, ValueError, KeyboardInterrupt):
            self.quit()
        except Exception as e:
            printException(e)
            self.quit()
