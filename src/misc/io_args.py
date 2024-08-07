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
from enum import Enum
from multiprocessing import Queue, Process
from typing import Callable

from misc.general_util import tprint, eprint


class DemodulationChoices(str, Enum):
    FM = "fm"
    AM = "am"
    REAL = "re"
    IMAG = "im"

    def __str__(self):
        return self.value


def selectDemodulation(demodType: DemodulationChoices, processor) -> Callable:
    tprint(f'{demodType} requested')
    if 'fm' == demodType or 'nfm' == demodType:
        return processor.selectOutputFm
    elif 'am' == demodType:
        return processor.selectOutputAm
    elif 're' == demodType:
        return processor.selectOutputReal
    elif 'im' == demodType:
        return processor.selectOutputImag
    raise ValueError(f'Invalid demod type {demodType}')


def selectPlotType(plotType: str):
    from importlib.util import find_spec

    if find_spec('pyqtgraph') is None:
        eprint('pyqtgraph not installed')
        return None
    else:
        if plotType == 'ps' or plotType == 'spec':
            from plots.spectrum_analyzer_plot import SpectrumAnalyzerPlot
            return SpectrumAnalyzerPlot
        elif plotType == 'vfos' or plotType == 'vfo':
            from plots.multi_spectrum_analyzer_plot import MultiSpectrumAnalyzerPlot
            return MultiSpectrumAnalyzerPlot
        elif plotType == 'water' or plotType == 'waterfall':
            from plots.waterfall_plot import WaterfallPlot
            return WaterfallPlot
    raise ValueError(f'Invalid plot type {plotType}')


class IOArgs:
    from multiprocessing import Value
    strct = None

    def __init__(self, verbose: int = 0, **kwargs):
        from misc.general_util import traceOn, verboseOn
        from misc.file_util import checkWavHeader
        IOArgs.strct = kwargs
        if verbose > 1:
            traceOn()
        elif verbose > 0:
            verboseOn()
        kwargs['fileInfo'] = checkWavHeader(kwargs['inFile'], kwargs['fs'], kwargs['enc'])
        kwargs['fs'] = kwargs['fileInfo']['sampRate']

        IOArgs._initializeOutputHandlers(**kwargs)
        kwargs['isDead'].value = 0

    @classmethod
    def _initializeProcess(cls, isDead: Value, processor, *args,
                           name: str = 'Process', **kwargs) -> tuple[Queue, Process]:
        if processor is None:
            raise ValueError('Processor must be provided')
        buffer = Queue()
        proc = Process(target=processor.processData, args=(isDead, buffer, *args), kwargs=kwargs)
        proc.name = name + str(processor)
        return buffer, proc

    @classmethod
    def _initializeOutputHandlers(cls,
                                  isDead: Value = None,
                                  fs: int = 0,
                                  dm: DemodulationChoices | str = None,
                                  outFile: str = None,
                                  simo: bool = False,
                                  pl: str = None,
                                  processes: list[Process] = None,
                                  buffers: list[Queue] = None,
                                  **kwargs) -> None:
        import os
        from misc.general_util import eprint

        if not simo:
            from dsp.dsp_processor import DspProcessor
            cls.strct['processor'] = DspProcessor
        else:
            from dsp.vfo_processor import VfoProcessor
            cls.strct['processor'] = VfoProcessor
        cls.strct['processor'] = cls.strct['processor'](fs, **kwargs)
        selectDemodulation(dm, cls.strct['processor'])()

        if pl is not None and len(pl) > 0:
            if 'posix' in os.name and 'DISPLAY' not in os.environ:
                eprint('Warning: Plot(s) selected, but no display(s) detected')
            else:
                for p in pl.split(','):
                    psplot = selectPlotType(p)
                    kwargs['bandwidth'] = cls.strct['processor'].bandwidth
                    if psplot is not None:
                        buffer, proc = cls._initializeProcess(isDead,
                                                              psplot,
                                                              fs, name="Plotter-",
                                                              **kwargs)
                        processes.append(proc)
                        buffers.append(buffer)

        buffer, proc = cls._initializeProcess(isDead,
                                              cls.strct['processor'],
                                              outFile,
                                              name="File writer-",
                                              **kwargs)
        processes.append(proc)
        buffers.append(buffer)
