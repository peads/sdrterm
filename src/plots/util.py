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
import string
from importlib.resources import files
from typing import Callable

from dsp.dsp_processor import DspProcessor
from plots.multi_vfo_plot import MultiVFOPlot
from plots.ps_plot import PowerSpectrumPlot
from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot
from plots.waterfall_plot import WaterfallPlot
from plots.wave_form_plot import WaveFormPlot


def selectDemodulation(demodType: str, processor: DspProcessor) -> Callable:
    if demodType == 'fm' or demodType == 'nfm':
        return processor.selectOuputFm
    elif demodType == 'wfm' or demodType == 'monofm':
        return processor.selectOuputWfm
    elif demodType == 'am':
        raise processor.selectOuputAm
    else:
        raise ValueError(f'Invalid plot type {demodType}')


def selectPlotType(plotType: string, processor: DspProcessor, dataType=None, iq=False):
    # stupid python not having switch fall-thru >:(
    if plotType == 'ps' or plotType == 'power':
        try:
            files('pyqtgraph')
            return SpectrumAnalyzerPlot
        except ModuleNotFoundError:
            return PowerSpectrumPlot(fs=processor.fs,
                                     processor=processor,
                                     centerFreq=processor.centerFreq,
                                     tunedFreq=processor.tunedFreq,
                                     bandwidth=processor.bandwidth,
                                     iq=iq)
    elif plotType == 'wave' or plotType == 'waveform':
        return WaveFormPlot(fs=processor.fs,
                            processor=processor,
                            centerFreq=processor.centerFreq,
                            iq=iq)
    elif plotType == 'water' or plotType == 'waterfall':
        return WaterfallPlot(fs=processor.fs,
                             processor=processor,
                             centerFreq=processor.centerFreq,
                             bandwidth=processor.bandwidth,
                             tunedFreq=processor.tunedFreq,
                             iq=iq)
    elif plotType == 'vfos' or plotType == 'vfo':
        return MultiVFOPlot(fs=processor.fs,
                            processor=processor,
                            centerFreq=processor.centerFreq,
                            bandwidth=processor.bandwidth,
                            tunedFreq=processor.tunedFreq,
                            vfos=processor.vfos,
                            dataType=dataType,
                            iq=iq)
    else:
        raise ValueError(f'Invalid plot type {plotType}')
