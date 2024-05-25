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
import os
import signal as s
from functools import partial
from itertools import chain
from multiprocessing import Pool

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import SubplotSpec
from scipy import fft

from dsp.util import shiftFreq
from plots.abstract_plot import Plot


class MultiVFOPlot(Plot):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.vfos is None:
            raise ValueError('vfos not specified')
        self.axes = None
        self.pool = None

    def initPlot(self):
        super().initPlot()
        size = np.sqrt(len(self.vfos))
        rows = int(np.ceil(size))
        cols = int(np.round(size))
        self.fig, self.ax = plt.subplots(rows, cols, layout='constrained')
        self.axes = []
        self.ln = []

        for i in range(rows):
            for j in range(cols):
                ax = self.ax[i][j]
                pos = ax.get_subplotspec().get_geometry()[2]
                if pos >= len(self.vfos):
                    k = pos - 1
                    self.fig.delaxes(ax)
                    self.axes[k].set_subplotspec(
                        SubplotSpec(self.axes[k].get_subplotspec().get_gridspec(), k,
                                    len(self.vfos)))
                    break
                else:
                    label = (self.tunedFreq + self.vfos[pos]) / 10E+5
                    self.axes.append(ax)
                    self.ln.append(ax.plot(0, 0)[0])
                    ax.set_xlim(-self.bandwidth, self.bandwidth)
                    xticks = ax.get_xticks()
                    xlabels = [str(round(x, 1)) for x in ax.get_xticks() / self.bandwidth + (
                            self.tunedFreq + self.vfos[pos]) / 10E+5]
                    ax.set_xticks(xticks, xlabels)
                    ax.set_ylim(-4, 2.5)
                    ax.set_xlabel(f'{label} [MHz]')
        plt.ioff()
        plt.show(block=False)
        self.initBlit()
        for i in range(len(self.vfos)):
            self.axes[i].draw_artist(self.ln[i])
        self.fig.canvas.blit(self.fig.bbox)
        last = self.vfos[-1]
        isOdd = len(self.vfos) & 1
        # scipy's 1D fft divides and conquers (likely recursively) and it inverts the list
        # order at the base case. if the len is odd, the last element becomes the mid-point
        self.vfos = list(reversed(list(chain.from_iterable(zip(self.vfos[1::2], self.vfos[::2])))))
        if isOdd:
            self.vfos.insert(len(self.vfos) // 2, last)

    @staticmethod
    def shiftVfos(y, fs, freq):
        return shiftFreq(y, freq, fs)

    def close(self):
        super().close()
        if hasattr(self, 'pool'):
            self.pool.close()
            self.pool.join()
            del self.pool

    def animate(self, y):

        if not self.isInit:
            if 'posix' in os.name:
                s.signal(s.SIGINT, s.SIG_IGN)  # https://stackoverflow.com/a/68695455/8372013
            self.pool = Pool()

        shift = self.pool.map_async(partial(self.shiftVfos, y, self.fs), self.vfos)
        fftData = fft.fft(shift.get(), norm='forward')
        fftData = fft.fftshift(fftData)
        amps = np.abs(fftData)
        amps = np.log10(amps * amps)
        freq = fft.fftfreq(len(y), 1 / self.fs)
        freq = fft.fftshift(freq)

        if not self.isInit:
            self.initPlot()

        self.fig.canvas.restore_region(self.bg)
        for i in range(0, len(self.vfos)):
            self.ln[i].set_ydata(amps[i])
            self.ln[i].set_xdata(freq)
            self.axes[i].draw_artist(self.ln[i])

        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
