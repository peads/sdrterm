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
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from dsp.util import applyFilters
from plots.abstract_plot import Plot


class WaveFormPlot(Plot):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.xdata = None

    def initPlot(self, n=1000):
        super().initPlot()
        self.fig, self.ax = plt.subplots()
        self.ln, = self.ax.plot(0, 0)
        self.ax.set_xlim(0, n)
        self.ax.set_ylim(-2, 2)
        self.xdata = np.arange(n)
        plt.ioff()
        plt.show(block=False)
        self.initBlit()

    def animate(self, y):
        if self.processor.decimation > 1:
            y = signal.decimate(y, self.processor.decimation, ftype='fir')

        y = signal.sosfilt(self.processor.sosIn, y)
        y = self.processor.demod(y)
        y = applyFilters(y, self.processor.outputFilters)

        if not self.isInit:
            self.initPlot(len(y))

        self.fig.canvas.restore_region(self.bg)
        self.ln.set_ydata(y)
        self.ln.set_xdata(self.xdata)
        self.ax.draw_artist(self.ln)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
