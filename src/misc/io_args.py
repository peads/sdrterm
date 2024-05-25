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
from multiprocessing import Pipe, Process
from typing import Iterable
from uuid import UUID, uuid4

from dsp.dsp_processor import DspProcessor
from dsp.vfo_processor import VfoProcessor
from misc.file_util import checkWavHeader
from misc.general_util import traceOn, verboseOn
from plots.util import selectDemodulation, selectPlotType


class IOArgs:
    pl = None
    pipes = None
    processes = None
    dm = None
    normalize = None
    vfos = None
    tuned = None
    center = None
    dec = None
    enc = None
    bits = None
    fs = None
    outFile = None
    inFile = None
    isDead = None
    omegaOut = None
    correctIq = None
    simo = None
    fileInfo = None
    processor = None

    def __init__(self, **kwargs):
        if 'verbose' in kwargs and kwargs['verbose']:
            verboseOn()
        if 'posix' in os.name and 'trace' in kwargs and kwargs['trace']:
            traceOn()
        IOArgs.simo = kwargs['simo']
        IOArgs.fs = kwargs['fs'] if 'fs' in kwargs else None
        IOArgs.inFile = kwargs['inFile']
        IOArgs.outFile = kwargs['outFile']
        IOArgs.dec = kwargs['dec'] if 'dec' in kwargs else None
        IOArgs.center = kwargs['center']
        IOArgs.tuned = kwargs['tuned'] if 'tuned' in kwargs else None
        if 'vfos' in kwargs and kwargs['vfos'] is not None:
            vfos = kwargs['vfos']
            IOArgs.vfos = [float(x) for x in vfos.split(',') if x is not None and len(x) > 0]
            IOArgs.vfos.append(0)
        IOArgs.dm = kwargs['dm'] if 'dm' in kwargs else None
        IOArgs.processes = kwargs['processes']
        IOArgs.pipes = kwargs['pipes']
        IOArgs.pl = kwargs['pl'] if 'pl' in kwargs else None
        IOArgs.isDead = kwargs['isDead']
        IOArgs.bits = kwargs['bits'] if 'bits' in kwargs else None
        IOArgs.enc = kwargs['enc'] if 'enc' in kwargs else None
        IOArgs.normalize = kwargs['normalize'] if 'normalize' in kwargs else False
        IOArgs.omegaOut = kwargs['omegaOut'] if 'omegaOut' in kwargs else None
        IOArgs.correctIq = kwargs['correctIq']

        IOArgs.initParameters()
        IOArgs.initIOHandlers()
        IOArgs.isDead.value = 0

    @classmethod
    def initParameters(cls):
        cls.fileInfo = checkWavHeader(cls.inFile, cls.fs, cls.bits, cls.enc)
        cls.fs = cls.fileInfo['sampRate']

    @classmethod
    def initIOHandlers(cls):
        if not cls.simo:
            processor = DspProcessor
        else:
            if not cls.vfos:
                raise ValueError("simo mode cannot be used without the vfos option")
            processor = VfoProcessor
        cls.processor = processor = processor(decimation=cls.dec,
                                              centerFreq=cls.center,
                                              tunedFreq=cls.tuned,
                                              vfos=cls.vfos,
                                              fs=cls.fs,
                                              normalize=cls.normalize,
                                              omegaOut=cls.omegaOut,
                                              correctIq=cls.correctIq)
        selectDemodulation(cls.dm, processor)()
        r, w = Pipe(False)
        fileWriter = Process(target=processor.processData,
                             args=(cls.isDead, (r, w), cls.outFile,))
        writerUuid = IOArgs.addConsumer(fileWriter, (r, w))
        fileWriter.name = "File writer-" + str(writerUuid)

        if cls.pl is not None and len(cls.pl) > 0:
            for p in cls.pl.split(','):
                psplot = selectPlotType(p, processor, cls.fileInfo['bitsPerSample'][1],
                                        cls.correctIq)
                r, w = Pipe(False)
                plotter = Process(target=psplot.processData,
                                  args=(cls.isDead, (r, w)))
                plotUuid = IOArgs.addConsumer(plotter, (r, w), uuid=psplot.uuid)
                plotter.name = "Plotter-" + str(plotUuid)

    @classmethod
    def addConsumer(cls, proc: Process,
                    pipe: Pipe,
                    uuid: UUID = None):
        if uuid is None:
            uuid = uuid4()

        cls.processes[uuid] = proc
        cls.pipes[uuid] = pipe
        return uuid


def closePipes(pipes: Iterable):
    for r, w in pipes:
        r.close()
        w.close()
