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
    def __init__(self, bandwidth: int = -1, vfos: str = None, tuned: int = 0, *args, **kwargs):
        # if vfos is None:
        #     raise ValueError("MultiSpectrumAnalyzerPlot cannot be used without the vfos option")
        kwargs['nfft'] = 8192
        super().__init__(*args, **kwargs)
        vfos = '' if vfos is None else vfos
        self.vfos = vfos.split(',')
        self.vfos = [int(vfo) for vfo in self.vfos if vfo is not None and len(vfo)]
        self.item.setXRange(-bandwidth, bandwidth)
        self.widgets = [self.widget]
        self.items = [self.item]
        self.lines = [self.line]
        self.axes = [self.axis]

        size = np.sqrt(len(self.vfos) + 1)
        cols = int(np.ceil(size))
        rows = int(np.round(size))

        bandwidth >>= 1
        self.axis.setLabel(tuned)
        self.item.setXRange(-bandwidth, bandwidth)
        import pyqtgraph as pg

        j = 1
        for i, vfo in enumerate(self.vfos, start=0):
            if j >= cols:
                j = 0
            if i >= rows:
                i = 1

            b = vfo
            widget = pg.PlotWidget()
            item = widget.getPlotItem()
            item.setXRange(-bandwidth + b, bandwidth + b)
            item.setYRange(-6, 4)
            item.setMouseEnabled(x=False, y=False)
            axis = item.getAxis("bottom")
            axis.setLabel(str(vfo + tuned))
            # TODO explore ViewBox::linkView
            line = item.plot()

            self.widgets.append(widget)
            self.items.append(item)
            self.lines.append(line)
            self.axes.append(axis)
            self.layout.addWidget(widget, j, i)
            j += 1
        self.window.setWindowTitle("MultiSpectrumAnalyzer")

    def update(self):
        try:
            nfft = self.nfft << 1
            if nfft < self.length:
                self.nfft = nfft
            super().update()
            for curve in self.lines:
                for amp in self.amps:
                    curve.setData(self.freq, amp)
        except KeyboardInterrupt:
            pass
        finally:
            self.quit()
            return
