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
import numpy as np

from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot


class MultiSpectrumAnalyzerPlot(SpectrumAnalyzerPlot):
    def __init__(self,
                 bandwidth: int = 1,
                 vfos: str = None,
                 *args,
                 **kwargs):
        if vfos is None:
            raise ValueError("MultiSpectrumAnalyzerPlot cannot be used without the vfos option")
        super().__init__(*args, **kwargs)
        vfos = '' if vfos is None else vfos
        self.vfos = vfos.split(',')
        self.vfos = [int(vfo) for vfo in self.vfos if vfo is not None and len(vfo)]
        self.item.setXRange(-bandwidth, bandwidth)
        self.items = [self.item]
        self.axes = [self.axis]

        size = np.sqrt(len(self.vfos) + 1)
        cols = int(np.ceil(size))
        rows = int(np.round(size))

        bandwidth >>= 1
        self.item.setXRange(-bandwidth, bandwidth)
        import pyqtgraph as pg

        j = 1
        for i, vfo in enumerate(self.vfos, start=0):
            if j >= cols:
                j = 0
            if i >= rows:
                i = 1

            widget = pg.PlotWidget()
            item = widget.getPlotItem()
            item.setXRange(-bandwidth + vfo, bandwidth + vfo)
            item.setYRange(-6, 4)
            item.setMouseEnabled(x=False, y=False)
            item.setMenuEnabled(False)
            item.showAxes(True, showValues=(False, False, False, True))
            item.hideButtons()
            axis = item.getAxis("bottom")
            axis.setLabel("Frequency [MHz]")

            self.widgets.append((widget, vfo))
            self.items.append(item)
            self.lines.append(item.plot())
            self.axes.append(axis)
            self.layout.addWidget(widget, j, i)
            j += 1
        self.window.setWindowTitle("MultiSpectrumAnalyzer")
