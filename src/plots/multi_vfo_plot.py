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
from matplotlib.gridspec import SubplotSpec
from scipy import fft

from dsp.util import shiftFreq
from plots.abstract_plot import Plot


class MultiVFOPlot(Plot):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if 'vfos' not in kwargs.keys() or not kwargs['vfos']:
            raise ValueError('vfos not specified')
        self.axes = None
        self.vfos = kwargs['vfos']
        self.vfos.insert(0, 0)
        self.xticks = (-1 / 2 + np.arange(1 / 8, 1, 1 / 8)) * self.bandwidth

    def initPlot(self):
        super().initPlot()
        size = len(self.vfos)
        squirt = int(np.sqrt(size))
        self.fig, self.ax = plt.subplots(squirt, squirt + size % squirt, layout='constrained')
        self.axes = [None] * size
        self.ln = [None] * size

        for i in range(len(self.ax)):
            for j in range(len(self.ax[0])):
                ax = self.ax[i][j]
                pos = ax.get_subplotspec().get_geometry()[2]
                if pos >= len(self.vfos):
                    self.fig.delaxes(ax)
                    self.axes[pos - 1].set_subplotspec(
                        SubplotSpec(self.axes[pos - 1].get_subplotspec().get_gridspec(), pos - 1, len(self.vfos)))
                else:
                    label = (self.tunedFreq + self.vfos[pos]) / 10E+5
                    self.axes[pos] = ax
                    self.ln[pos] = ax.plot(0, 0)[0]
                    ax.set_xlim(-self.bandwidth, self.bandwidth)
                    ax.set_ylim(0, 10)
                    ax.set_xlabel(f'{label} [MHz]')
        plt.ioff()
        plt.show(block=False)
        self.initBlit()
        for i in range(len(self.axes)):
            self.axes[i].draw_artist(self.ln[i])
        self.fig.canvas.blit(self.fig.bbox)

    def animate(self, y):
        if not self.isInit:
            self.initPlot()

        self.fig.canvas.restore_region(self.bg)
        n = len(y)
        for i in range(len(self.vfos)):
            fftData = fft.fft(shiftFreq(y, self.vfos[i], self.fs), norm='forward')
            fftData = fft.fftshift(fftData)
            amps = np.abs(fftData)
            amps = np.sqrt(amps * amps)
            freq = fft.fftfreq(n, 1 / self.fs)
            freq = fft.fftshift(freq)

            self.ln[i].set_ydata(amps)
            self.ln[i].set_xdata(freq)

            self.axes[i].draw_artist(self.ln[i])

        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
