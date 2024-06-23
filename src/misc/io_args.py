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
import os
from multiprocessing import Process, Queue, Value
from uuid import uuid4

from dsp.dsp_processor import DspProcessor
from dsp.vfo_processor import VfoProcessor
from misc.file_util import checkWavHeader
from misc.general_util import traceOn, verboseOn, eprint
from plots.util import selectDemodulation, selectPlotType


class IOArgs:
    strct = None

    def __init__(self, **kwargs):
        IOArgs.strct = kwargs
        if 'verbose' in kwargs and kwargs['verbose']:
            verboseOn()
        if 'trace' in kwargs and kwargs['trace']:
            traceOn()
        kwargs['fileInfo'] = checkWavHeader(kwargs['inFile'], kwargs['fs'], kwargs['enc'])
        kwargs['fs'] = kwargs['fileInfo']['sampRate']
        kwargs['buffers'] = []

        IOArgs.__initializeOutputHandlers(**kwargs)
        kwargs['isDead'].value = 0

    @classmethod
    def __initializeOutputHandlers(cls,
                                   isDead: Value = None,
                                   fs: int = 0,
                                   dm: str = None,
                                   outFile: str = None,
                                   simo: bool = False,
                                   pl: str = None,
                                   processes: list[Process] = None,
                                   buffers = None,
                                   **kwargs):
        cls.strct['processor'] = DspProcessor if not simo else VfoProcessor
        cls.strct['processor'] = cls.strct['processor'](fs, **kwargs)
        selectDemodulation(dm, cls.strct['processor'])()

        buffer = Queue()
        buffers.append(buffer)

        fileWriter = Process(target=cls.strct['processor'].processData,
                             args=(isDead, buffer, outFile))
        fileWriter.name = "File writer-" + type(cls.strct['processor']).__name__
        processes.append(fileWriter)

        if pl is not None and len(pl) > 0:
            if 'posix' in os.name and 'DISPLAY' not in os.environ:
                eprint('Warning: No display detected, but plots selected')
            else:
                for p in pl.split(','):
                    buffer = Queue()
                    buffers.append(buffer)
                    psplot = selectPlotType(p)
                    kwargs['bandwidth'] = cls.strct['processor'].bandwidth
                    plotter = Process(target=psplot.processData,
                                      args=(isDead, buffer, fs),
                                      kwargs=kwargs,
                                      daemon=True)
                    processes.append(plotter)
                    plotter.name = "Plotter-" + type(psplot).__name__
