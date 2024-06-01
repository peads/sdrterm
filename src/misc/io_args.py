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
import json
import os
from multiprocessing import Pipe, Process
from uuid import UUID, uuid4

from dsp.dsp_processor import DspProcessor
from dsp.vfo_processor import VfoProcessor
from misc.hooked_thread import HookedThread
from misc.file_util import checkWavHeader
from misc.general_util import traceOn, verboseOn, tprint
from plots.util import selectDemodulation, selectPlotType

class VfoList(list):
    def __init__(self, vfos, freq=0, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if vfos is None or len(vfos) < 1:
            raise ValueError('VFOs csv cannot be empty')

        self.extend([float(x) for x in vfos.split(',') if x is not None and len(x) > 0])
        self.append(0)
        self._freq = freq

    def __repr__(self) -> str:
        d = dict()
        d['vfos'] = [(f + self._freq) / 10E+5 for f in self]
        return json.dumps(d, indent=2)


class IOArgs:
    pl = None
    pipes = None
    processes = None
    dm = None
    normalize = False
    vfos = None
    tuned = 0
    center = 0
    dec = 0
    enc = None
    bits = None
    fs = 0
    outFile = None
    inFile = None
    isDead = None
    omegaOut = 0
    correctIq = None
    simo = False
    fileInfo = None
    processor = None

    def __init__(self, **kwargs):
        if 'verbose' in kwargs and kwargs['verbose']:
            verboseOn()
        if 'trace' in kwargs and kwargs['trace']:
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
            IOArgs.vfos = VfoList(vfos=vfos, freq=IOArgs.tuned)
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
        IOArgs.fileInfo = checkWavHeader(IOArgs.inFile, IOArgs.fs, IOArgs.bits, IOArgs.enc)
        IOArgs.fs = IOArgs.fileInfo['sampRate']

        IOArgs.__initIOHandlers()
        IOArgs.isDead.value = 0
        tprint(IOArgs.vfos)


    @classmethod
    def __initIOHandlers(cls):
        processor = DspProcessor if not cls.simo else VfoProcessor
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
        fileWriter = HookedThread(isDead=cls.isDead, target=processor.processData,
                                  args=(cls.isDead, (r, w), cls.outFile,))
        writerUuid = IOArgs.addConsumer(fileWriter, (r, w))
        fileWriter.name = "File writer-" + str(writerUuid)

        if cls.pl is not None and len(cls.pl) > 0:
            for p in cls.pl.split(','):
                psplot = selectPlotType(p, processor, cls.fileInfo['bitsPerSample'][1],
                                        cls.correctIq)
                r, w = Pipe(False)
                # annoying, but plots don't seem to like BeInG rUn On NoT ThE mAiN tHrEaD
                # also, it's more calculation(cpu)-bound due the graphs' data generation/manipulation rather than
                # the more I/O-y-bound displaying bit anyway
                plotter = Process(target=psplot.processData, args=(cls.isDead, (r, w)))
                plotUuid = IOArgs.addConsumer(plotter, (r, w), uuid=psplot.uuid)
                plotter.name = "Plotter-" + str(plotUuid)

    @classmethod
    def addConsumer(cls, proc, pipe: Pipe, uuid: UUID = None):
        if uuid is None:
            uuid = uuid4()

        cls.processes[uuid] = proc
        cls.pipes[uuid] = pipe
        return uuid
