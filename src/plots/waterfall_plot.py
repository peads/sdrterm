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
from scipy.signal import ShortTimeFFT

from plots.abstract_plot import Plot


class WaterfallPlot(Plot):
    NPERSEG = 1024
    NOOVERLAP = NPERSEG >> 1
    NFFT = NPERSEG

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.t = 0
        self.dt = 1
        self._SFT = ShortTimeFFT.from_window(('kaiser', 5),
                                             self.fs,
                                             self.NPERSEG,
                                             self.NOOVERLAP,
                                             mfft=self.NFFT,
                                             fft_mode='centered',
                                             scale_to='magnitude',
                                             phase_shift=None)
        self.pad_xextent = (self.NFFT - self.NOOVERLAP) / (self.fs * 2)

    def initPlot(self):
        super().initPlot()
        self.fig, self.ax = plt.subplots()

        xticks = (-1 / 2 + np.arange(0, 9/8, 1 / 8)) * self.fs
        xlabels = [str(round(x, 3)) for x in xticks / self.fs + self.tunedFreq / 10E+5]
        self.ax.set_yticks([])
        self.ax.set_xticks(xticks, xlabels)
        if self.tunedFreq:
            self.ax.set_xlabel(f'{self.tunedFreq / 10E+5} [MHz]')
        plt.ioff()
        plt.show(block=False)
        self.initBlit()
        # self.fig.canvas.mpl_connect('resize_event', self.resize)


    # def resize(self, _):
    #     self.ax.set_xticks(self.xticks)
    #     # self.ax.autoscale_view()
    #     self.ax.relim(visible_only=True)
    #     self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
    #     self.fig.canvas.restore_region(self.bg)
    #     # self.fig.draw_without_rendering()
    #     self.fig.canvas.blit(self.fig.bbox)
    #     self.fig.canvas.flush_events()

    def animate(self, y):
        Zxx = self._SFT.stft(y)
        extent = xmin, xmax, fmin, fmax = self._SFT.extent(len(y), center_bins=True)
        xmin -= self.pad_xextent
        xmax += self.pad_xextent

        if not self.isInit:
            self.initPlot()

        self.fig.canvas.restore_region(self.bg)
        self.ln = self.ax.imshow(np.flipud(10. * np.log10(np.abs(Zxx).T)),
                                 extent=extent,
                                 aspect="auto",
                                 animated=True)
        self.ax.draw_artist(self.ln)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
