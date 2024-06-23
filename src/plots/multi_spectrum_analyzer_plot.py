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

from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot


class MultiSpectrumAnalyzerPlot(SpectrumAnalyzerPlot):
    def __init__(self, bandwidth: int = -1, vfos: str = None, tuned: int = 0, *args, **kwargs):
        if vfos is None:
            raise ValueError("MultiSpectrumAnalyzerPlot cannot be used without the vfos option")
        kwargs['nfft'] = 8192
        super().__init__(*args, **kwargs)
        self.vfos = vfos.split(',')
        self.vfos = [int(vfo) for vfo in self.vfos if vfo is not None]
        self.item.setXRange(-bandwidth, bandwidth)
        self.widgets = [self.widget]
        self.items = [self.item]
        self.curves = [self.curve_spectrum]
        self.axes = [self.axis]

        bandwidth >>= 1
        self.axis.setLabel(tuned)
        self.item.setXRange(-bandwidth, bandwidth)
        import pyqtgraph as pg
        for vfo in self.vfos:
            b = vfo
            widget = pg.PlotWidget()
            item = widget.getPlotItem()
            item.setXRange(-bandwidth + b, bandwidth + b)
            item.setYRange(-6, 4)
            item.setMouseEnabled(x=False, y=False)
            axis = item.getAxis("bottom")
            axis.setLabel(str(vfo + tuned))
            curve = item.plot()

            self.widgets.append(widget)
            self.items.append(item)
            self.curves.append(curve)
            self.axes.append(axis)
            self.layout.addWidget(widget)
        self.window.setWindowTitle("MultiSpectrumAnalyzer")

    def update(self):
        from pyqtgraph.Qt.QtCore import QCoreApplication
        nfft = self.nfft << 1
        if nfft < self.length:
            self.nfft = nfft
        try:
            super().update()
            for curve in self.curves:
                for amp in self.amps:
                    curve.setData(self.freq, amp)
        except KeyboardInterrupt:
            QCoreApplication.quit()
