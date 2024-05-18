#!/usr/bin/env python3
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
import sys
from multiprocessing import Pipe, Process, Value
from typing import Annotated, Iterable
from uuid import UUID, uuid4

import typer

from dsp.dsp_processor import DspProcessor
from dsp.vfo_processor import VfoProcessor
from misc.file_util import checkWavHeader
from misc.general_util import eprint, printException
from misc.read_file import readFile
from plots.util import selectDemodulation, selectPlotType


# matplotlib.use('QtAgg')
# print(plt.rcParams['backend'])
# print(plt.get_backend(), matplotlib.__version__)
# plt.get_backend(), matplotlib.__version__
#

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

    def __init__(self, **kwargs):
        IOArgs.simo = kwargs['simo']
        IOArgs.fs = kwargs['fs'] if 'fs' in kwargs else None
        IOArgs.inFile = kwargs['inFile']
        IOArgs.outFile = kwargs['outFile']
        IOArgs.dec = kwargs['dec'] if 'dec' in kwargs else None
        IOArgs.center = float(kwargs['center'])
        IOArgs.tuned = kwargs['tuned'] if 'tuned' in kwargs else None
        if 'vfos' in kwargs and kwargs['vfos'] is not None:
            vfos = kwargs['vfos']
            IOArgs.vfos = [float(x) for x in vfos.split(',')]
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

        IOArgs.outFile = 'NUL' if IOArgs.outFile is not None and '/dev/null' in IOArgs.outFile and 'POSIX' not in os.name else IOArgs.outFile
        IOArgs.initParameters()
        IOArgs.initIOHandlers()
        IOArgs.isDead.value = 0

    @classmethod
    def initParameters(cls):
        cls.inFile = sys.stdin.fileno() if cls.inFile is None else cls.inFile
        cls.outFile = sys.stdout.fileno() if cls.outFile is None else cls.outFile
        cls.fileInfo = checkWavHeader(cls.inFile, cls.fs, cls.bits, cls.enc)
        cls.fs = cls.fileInfo['sampRate']

    @classmethod
    def initIOHandlers(cls):
        processor = VfoProcessor if hasattr(os, 'mkfifo') and cls.simo and cls.vfos else DspProcessor
        processor = processor(decimation=cls.dec,
                              centerFreq=cls.center,
                              tunedFreq=cls.tuned,
                              vfos=cls.vfos,
                              fs=cls.fs,
                              normalize=cls.normalize,
                              omegaOut=cls.omegaOut)
        selectDemodulation(cls.dm, processor)()
        r, w = Pipe(False)
        fileWriter = Process(target=processor.processData,
                             args=(cls.isDead, (r, w), cls.outFile,))
        writerUuid = IOArgs.addConsumer(fileWriter, (r, w), uuid=UUID(int=1))
        fileWriter.name = "File writer-" + str(writerUuid)

        if cls.pl is not None and len(cls.pl) > 0:
            for p in cls.pl.split(','):
                psplot = selectPlotType(p, processor, cls.fileInfo['bitsPerSample'][1], cls.correctIq)
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


def main(fs: Annotated[int, typer.Option(show_default=False, help='Sampling frequency in Samples/s')] = None,
         center: Annotated[str, typer.Option('--center-frequency', '-c', help='Offset from tuned frequency in Hz')] = '0',
         inFile: Annotated[str, typer.Option('--input', '-i', show_default='stdin', help='Input device')] = None,
         outFile: Annotated[str, typer.Option('--output', '-o', show_default='stdout', help='Output device')] = None,
         pl: Annotated[str, typer.Option('--plot', help='1D-Comma-separated value of plot type(s)')] = None,
         dm: Annotated[str, typer.Option('--demod', help='Demodulation type')] = 'fm',
         tuned: Annotated[int, typer.Option('--tuned-frequency', '-t', help='Tuned frequency in Hz')] = None,
         vfos: Annotated[str, typer.Option(help='1D-Comma-separated value of offsets from center frequency to process in addition to center in Hz')] = None,
         dec: Annotated[int, typer.Option('--decimation', help='Log2 of decimation factor (i.e. x where 2^x is the decimation factor))')] = None,
         bits: Annotated[int, typer.Option('--bits-per-sample', '-b', help='Bits per sample (ignored if wav file)')] = None,
         enc:  Annotated[str, typer.Option('--encoding', '-e', help='Binary encoding (ignored if wav file)')] = None,
         normalize: Annotated[bool, typer.Option(help='Toggle normalizing input analytic signal')] = False,
         omegaOut: Annotated[int, typer.Option('--omega-out', '-m', help='Cutoff frequency in Hz')] = 9500,
         correct_iq: Annotated[bool, typer.Option(help='Toggle iq correction for visualization')] = False,
         use_file_buffer: Annotated[bool, typer.Option(help="Toggle buffering full file to memory before processing. Obviously, this doesn't include when reading from stdin")] = True,
         simo: Annotated[bool, typer.Option(help='EXPERIMENTAL enable using named pipes to output data processed from multiple channels specified by the vfos option')] = False):

    processes: dict[UUID, Process] = {}
    pipes: dict[UUID, Pipe] = {}
    isDead = Value('i', 0)
    ioArgs = IOArgs(fs=fs,
                    inFile=inFile,
                    outFile=outFile,
                    dec=dec,
                    center=center,
                    tuned=tuned,
                    vfos=vfos,
                    dm=dm,
                    processes=processes,
                    pipes=pipes,
                    pl=pl,
                    isDead=isDead,
                    omegaOut=omegaOut,
                    bits=bits,
                    enc=enc,
                    normalize=normalize,
                    correctIq=correct_iq,
                    simo=simo)
    try:
        for proc in processes.values():
            proc.start()

        readFile(processes=processes,
                 pipes=pipes,
                 isDead=isDead,
                 offset=ioArgs.fileInfo['dataOffset'],
                 wordtype=ioArgs.fileInfo['bitsPerSample'],
                 f=ioArgs.inFile,
                 fullFileRead=use_file_buffer)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        printException(e)
    finally:
        isDead.value = 1
        eprint('Main halted')


if __name__ == '__main__':
    typer.run(main)
