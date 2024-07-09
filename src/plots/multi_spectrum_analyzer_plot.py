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
from numpy import sqrt, round, ceil

from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot


class MultiSpectrumAnalyzerPlot(SpectrumAnalyzerPlot):
    def __init__(self,
                 bandwidth: int,
                 vfos: str = None,
                 *args,
                 **kwargs):
        if vfos is None:
            raise ValueError("MultiSpectrumAnalyzerPlot cannot be used without the vfos option")

        from pyqtgraph import PlotWidget
        super().__init__(*args, **kwargs)

        self.widgets = []
        vfos = '' if vfos is None else vfos
        self.vfos = vfos.split(',')
        self.vfos = [int(vfo) for vfo in self.vfos if vfo is not None and len(vfo)]

        size = sqrt(len(self.vfos) + 1)
        cols = int(ceil(size))
        rows = int(round(size))

        bandwidth >>= 1
        self.item.setXRange(-bandwidth, bandwidth, padding=0)
        self.item.setYRange(-10, 10, padding=0)
        self.widgets.append((self.widget, 0))

        j = 1
        for i, vfo in enumerate(self.vfos, start=0):
            if j >= cols:
                j = 0
            if i >= rows:
                i = 1

            widget = PlotWidget()
            item = widget.getPlotItem()
            axis = item.getAxis("bottom")

            item.setXRange(-bandwidth + vfo, bandwidth + vfo)
            item.setYRange(-10, 10, padding=0)
            item.setMouseEnabled(x=False, y=False)
            item.setMenuEnabled(False)
            item.showAxes(self._AXES, showValues=self._AXES_VALUES)
            item.hideButtons()

            plot = item.plot()
            self.plots.append(plot)
            self.widgets.append((widget, vfo))
            self.layout.addWidget(widget, j, i)

            axis.setLabel("Frequency", units="Hz", unitPrefix="M")
            j += 1
        self.window.setWindowTitle("MultiSpectrumAnalyzer")
        self._setTicks(bandwidth)
