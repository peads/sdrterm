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

from plots.abstract_plot import Plot


class WaveFormPlot(Plot):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.xdata = None

    def initPlot(self, n):
        super().initPlot()
        self.fig, self.ax = plt.subplots()
        self.ln, = self.ax.plot(0, 0)
        plt.ioff()
        plt.show(block=False)
        self.ax.set_xlim(0, n)
        self.ax.set_ylim(-1, 1)
        self.xdata = np.arange(n)
        self.initBlit()

    def animate(self, y):
        n = len(y)
        if not self.isInit:
            self.initPlot(n)

        self.fig.canvas.restore_region(self.bg)
        self.ln.set_ydata(y)
        self.ln.set_xdata(self.xdata)
        self.ax.draw_artist(self.ln)
        self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.flush_events()
