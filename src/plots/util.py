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
from misc.general_util import eprint, printException
from plots.multi_spectrum_analyzer_plot import MultiSpectrumAnalyzerPlot
from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot
from plots.waterfall_plot import WaterfallPlot


def selectDemodulation(demodType: str, processor: DspProcessor) -> Callable:
    if demodType == 'fm' or demodType == 'nfm':
        return processor.selectOuputFm
    elif demodType == 'wfm':
        return processor.selectOuputWfm
    elif demodType == 'am':
        raise processor.selectOuputAm
    else:
        raise ValueError(f'Invalid demod type {demodType}')


def selectPlotType(plotType: string):
    try:
        files('pyqtgraph')
        if plotType == 'ps' or plotType == 'spec':
            return SpectrumAnalyzerPlot
        elif plotType == 'vfos' or plotType == 'vfo':
            return MultiSpectrumAnalyzerPlot
        elif plotType == 'water' or plotType == 'waterfall':
            return WaterfallPlot
        else:
            eprint(f'Invalid plot type {plotType}')
    except ModuleNotFoundError as e:
        printException(e)
        return None
