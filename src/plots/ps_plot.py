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
from scipy import fft

from plots.abstract_plot import Plot


class PowerSpectrumPlot(Plot):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.xticks = (-1 / 2 + np.arange(1 / 8, 1, 1 / 8)) * self.fs

    def initPlot(self):
        super().initPlot()
        self.fig, self.ax = plt.subplots()
        self.ln, = self.ax.plot(0, 0)
        self.ax.set_ylim(-2, 2.5)
        self.ax.set_xlim(self.xticks[0], self.xticks[-1])
        self.ax.set_xticks(self.xticks)
        if self.tunedFreq:
            self.ax.set_xlabel(f'{self.tunedFreq / 10E+5} [MHz]')
        plt.ioff()
        plt.show(block=False)
        self.initBlit()

    def animate(self, y):
        if not self.isInit:
            self.initPlot()
        fftData = fft.fft(y, norm='forward')
        fftData = fft.fftshift(fftData)
        amps = np.abs(fftData)
        amps = np.log10(np.sqrt(amps * amps))
        freq = fft.fftfreq(len(y), 1 / self.fs)
        freq = fft.fftshift(freq)

        self.fig.canvas.restore_region(self.bg)
        self.ln.set_ydata(amps)
        self.ln.set_xdata(freq)
        self.ax.draw_artist(self.ln)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
