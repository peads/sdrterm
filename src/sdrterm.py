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
import atexit
import sys
from multiprocessing import Pipe, Process, Value
from typing import Annotated, Iterable
from uuid import UUID, uuid4

import typer

from dsp.dsp_processor import DspProcessor
from misc.file_util import checkWavHeader
from misc.general_util import eprint, printException
from misc.read_file import readFile
from plots.util import selectDemodulation, selectPlotType


# matplotlib.use('QtAgg')
# print(plt.rcParams['backend'])
# print(plt.get_backend(), matplotlib.__version__)
# plt.get_backend(), matplotlib.__version__
#
class ExitHooks(object):
    # https://stackoverflow.com/a/9741784/8372013
    def __init__(self):
        self._orig_exit = None
        self.exit_code = None
        self.exception = None

    def hook(self):
        self._orig_exit = sys.exit
        sys.exit = self.exit
        sys.excepthook = self.exc_handler

    def exit(self, code=0):
        self.exit_code = code
        self._orig_exit(code)

    def exc_handler(self, __, exc, *_):
        self.exception = exc

    def describe(self):
        if hooks.exit_code is not None:
            eprint(f"death by sys.exit({self.exit_code})")
        elif hooks.exception is not None:
            eprint(f"death by exception: {self.exception}")


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

    def __init__(self,
                 fs: int,
                 inFile: str,
                 outFile: str,
                 dec: int,
                 center: str,
                 tuned: int,
                 vfos: str,
                 dm: str,
                 processes,
                 pipes,
                 pl: str,
                 isDead,
                 omegaOut: int,
                 bits: int = None,
                 enc: str = None,
                 normalize: bool = False,
                 correctIq: bool = False):
        IOArgs.fs = fs
        IOArgs.inFile = inFile
        IOArgs.outFile = outFile
        IOArgs.dec = dec
        IOArgs.center = float(center)
        IOArgs.tuned = tuned
        IOArgs.vfos = [float(x) for x in vfos.split(',')] if not (
                vfos is None or len(vfos) < 1) else []
        IOArgs.vfos.insert(0, 0)
        IOArgs.dm = dm
        IOArgs.processes = processes
        IOArgs.pipes = pipes
        IOArgs.pl = pl
        IOArgs.isDead = isDead
        IOArgs.bits = bits
        IOArgs.enc = enc
        IOArgs.normalize = normalize
        IOArgs.omegaOut = omegaOut
        IOArgs.correctIq = correctIq
        IOArgs.initParameters()
        IOArgs.initIOHandlers()
        isDead.value = 0

    @classmethod
    def initParameters(cls):
        cls.inFile = sys.stdin.fileno() if cls.inFile is None else cls.inFile
        cls.outFile = sys.stdout.fileno() if cls.outFile is None else cls.outFile
        cls.fileInfo = checkWavHeader(cls.inFile, cls.fs, cls.bits, cls.enc)
        cls.fs = cls.fileInfo['sampRate']

    @classmethod
    def initIOHandlers(cls):
        processor = DspProcessor(decimation=cls.dec,
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
         i: Annotated[str, typer.Option('--input', '-i', show_default='stdin', help='Input device')] = None,
         o: Annotated[str, typer.Option('--output', '-o', show_default='stdout', help='Output device')] = None,
         pl: Annotated[str, typer.Option('--plot', help='1D-Comma-separated value of plot type(s)')] = None,
         dm: Annotated[str, typer.Option('--demod', help='Demodulation type')] = 'fm',
         tuned: Annotated[int, typer.Option('--tuned-frequency', '-t', help='Tuned frequency in Hz')] = None,
         vfos: Annotated[str, typer.Option(help='1D-Comma-separated value of offsets from center frequency to process in addition to center in Hz')] = None,
         dec: Annotated[int, typer.Option('--decimation', help='Log2 of decimation factor (i.e. x where 2^x is the decimation factor))')] = None,
         bits: Annotated[int, typer.Option('--bits-per-sample', '-b', help='Bits per sample (ignored if wav file)')] = None,
         enc:  Annotated[str, typer.Option('--encoding', '-e', help='Binary encoding (ignored if wav file)')] = None,
         normalize: Annotated[bool, typer.Option(help='Normalize input analytic signal')] = False,
         omegaOut: Annotated[int, typer.Option('--omega-out', '-m', help='Cutoff frequency in Hz')] = 9500,
         correctIq: Annotated[bool, typer.Option('--correct-iq', '-q', help='Correct IQ for visualization')] = False):

    processes: dict[UUID, Process] = {}
    pipes: dict[UUID, Pipe] = {}
    isDead = Value('i', 0)
    ioArgs = IOArgs(fs, i, o, dec,
                    center, tuned, vfos,
                    dm, processes, pipes,
                    pl, isDead, omegaOut,
                    bits, enc, normalize, correctIq)

    try:
        for proc in processes.values():
            proc.start()

        readFile(processes=processes,
                 pipes=pipes,
                 isDead=isDead,
                 offset=ioArgs.fileInfo['dataOffset'],
                 wordtype=ioArgs.fileInfo['bitsPerSample'],
                 f=ioArgs.inFile)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        printException(e)
    finally:
        isDead.value = 1
        eprint('Main halted')


if __name__ == '__main__':
    hooks = ExitHooks()
    hooks.hook()
    atexit.register(hooks.describe)
    typer.run(main)
