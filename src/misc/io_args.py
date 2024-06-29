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
from multiprocessing import Process, Queue, Value

from dsp.data_processor import DataProcessor


class IOArgs:
    strct = None

    def __init__(self, verbose: int = 0, **kwargs):
        from misc.general_util import traceOn, verboseOn
        from misc.file_util import checkWavHeader
        IOArgs.strct = kwargs
        if 1 == verbose:
            verboseOn()
        elif verbose > 1:
            traceOn()
        kwargs['fileInfo'] = checkWavHeader(kwargs['inFile'], kwargs['fs'], kwargs['enc'])
        kwargs['fs'] = kwargs['fileInfo']['sampRate']
        kwargs['buffers'] = []

        IOArgs.__initializeOutputHandlers(**kwargs)
        kwargs['isDead'].value = 0

    @classmethod
    def __initializeProcess(cls, isDead: Value, processor: DataProcessor, *args,
                            name: str = 'Process', **kwargs) -> tuple[Queue, Process]:
        buffer = Queue()
        proc = Process(target=processor.processData, args=(isDead, buffer, *args), kwargs=kwargs)
        proc.name = name + type(processor).__name__
        return buffer, proc

    @classmethod
    def __initializeOutputHandlers(cls,
                                   isDead: Value = None,
                                   fs: int = 0,
                                   dm: str = None,
                                   outFile: str = None,
                                   simo: bool = False,
                                   pl: str = None,
                                   processes: list[Process] = None,
                                   buffers: list[Queue] = None,
                                   **kwargs) -> None:
        import os
        from dsp.dsp_processor import DspProcessor
        from dsp.vfo_processor import VfoProcessor
        from misc.general_util import eprint
        from plots.util import selectDemodulation, selectPlotType

        cls.strct['processor'] = DspProcessor if not simo else VfoProcessor
        cls.strct['processor'] = cls.strct['processor'](fs, **kwargs)
        selectDemodulation(dm, cls.strct['processor'])()

        if pl is not None and len(pl) > 0:
            if 'posix' in os.name and 'DISPLAY' not in os.environ:
                eprint('Warning: Plot(s) selected, but no display(s) detected')
            else:
                for p in pl.split(','):
                    psplot = selectPlotType(p)
                    kwargs['bandwidth'] = cls.strct['processor'].bandwidth
                    buffer, proc = cls.__initializeProcess(isDead,
                                                           psplot,
                                                           fs, name="Plotter-" + type(psplot).__name__,
                                                           **kwargs)
                    processes.append(proc)
                    buffers.append(buffer)

        buffer, proc = cls.__initializeProcess(isDead,
                                               cls.strct['processor'],
                                               outFile,
                                               name="File writer-" + type(cls.strct['processor']).__name__,
                                               **kwargs)
        processes.append(proc)
        buffers.append(buffer)