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
from datetime import datetime
from enum import Enum
from multiprocessing import get_all_start_methods, Process, Queue, Value
from os import path, getpid, unlink
from re import sub
from tempfile import gettempdir
from typing import Annotated
from uuid import uuid4

from click import BadParameter
from typer import run as typerRun, Option

from misc.file_util import DataType
from misc.general_util import eprint, setSignalHandlers, vprint, tprint, printException


class DemodulationChoices(str, Enum):
    FM = "fm"
    WFM = "wfm"
    AM = "am"
    REAL = "re"
    IMAG = "im"
    FFT = "fft"

    def __str__(self):
        return self.value


def parseStrDataType(value: str) -> str:
    try:
        return DataType[value].name
    except Exception as ex:
        raise BadParameter(str(ex))


def parseIntString(value: str) -> int:
    if value is None:
        raise BadParameter('Value cannot be None')
    elif 'k' in value:
        return int(float(value.replace('k', '')) * 10E+2)
    elif 'M' in value:
        return int(float(value.replace('M', '')) * 10E+5)
    try:
        return int(float(value))
    except Exception as ex:
        raise BadParameter(str(ex))


def main(fs: Annotated[int, Option('--fs', '-r',
                                   metavar='NUMBER',
                                   parser=parseIntString,
                                   show_default=False,
                                   help='Sampling frequency in k/M/Samples per sec')] = None,
         center: Annotated[int, Option('--center-frequency', '-c',
                                       metavar='NUMBER',
                                       parser=parseIntString,
                                       help='Offset from tuned frequency in k/M/Hz')] = '0',
         inFile: Annotated[str, Option('--input', '-i',
                                       show_default='stdin',
                                       help='Input device')] = None,
         outFile: Annotated[str, Option('--output', '-o',
                                        show_default='stdout',
                                        help='Output device')] = None,
         plot: Annotated[str, Option('--plot', help='1D-Comma-separated value of plot type(s)')] = None,
         demod: Annotated[DemodulationChoices, Option('--demodulation', '-m',
                                                      case_sensitive=False,
                                                      help='Demodulation type')] = DemodulationChoices.FM,
         tuned: Annotated[int, Option('--tuned-frequency', '-t',
                                      metavar='NUMBER',
                                      parser=parseIntString,
                                      help='Tuned frequency in k/M/Hz')] = '0',
         vfos: Annotated[str, Option(
             help='1D-Comma-separated value of offsets from tuned frequency to process in addition to tuned frequency in k/M/Hz')] = None,
         dec: Annotated[int, Option('--decimation', '-d', help='Decimation factor', min=2)] = 2,
         enc: Annotated[str, Option('--encoding', '-e',
                                    metavar='[' + '|'.join(DataType.dict().keys()) + ']',
                                    parser=parseStrDataType,

                                    help='Binary encoding (ignored if wav file)')] = None,
         omegaOut: Annotated[int, Option('--omega-out', '-w',
                                         metavar='NUMBER',
                                         parser=parseIntString,
                                         help='Output cutoff frequency in k/M/Hz')] = '12500',
         correct_iq: Annotated[bool, Option(help='Toggle iq correction')] = False,
         simo: Annotated[bool, Option(help='''
            Enable using sockets to output data processed from multiple channels specified by the vfos option.
            N.B. unlike normal mode, which uses the system-default endianness for output, the sockets output 
            network-default, big-endian doubles. [Implies: --vfos <csv>]''')] = False,
         verbose: Annotated[int, Option("--verbose", "-v",
                                        count=True,
                                        help='Toggle verbose output. Repetition increases verbosity (e.g. -vv, or -v -v)')] = 0,
         smooth_output: Annotated[int, Option(
             help='Provide length of polynomial for smoothing output with Savitzky–Golay filter. A larger polynomial implies more aggressive filtering.',
             show_default='0 => no filtering')] = 0,
         vfo_host: Annotated[
             str, Option(help='Address on which to listen for vfo client connections')] = 'localhost',
         swap_input_endianness: Annotated[bool, Option('--swap-input-endianness', '-X',
                                                       help='Swap input endianness',
                                                       show_default='False => system-default, or as defined in RIFF header')] = False,
         normalize_input: Annotated[bool, Option(help='Normalize input data.')] = False,):
    from misc.general_util import printException, eprint, tprint
    from misc.io_args import IOArgs
    from misc.read_file import readFile
    processes: list[Process] = []
    buffers: list[Queue] = []

    try:
        ioArgs = IOArgs(fs=fs,
                        inFile=inFile,
                        outFile=outFile,
                        dec=dec,
                        center=center,
                        tuned=tuned,
                        vfos=vfos,
                        dm=demod,
                        processes=processes,
                        buffers=buffers,
                        pl=plot,
                        isDead=isDead,
                        omegaOut=omegaOut,
                        enc=enc,
                        correctIq=correct_iq,
                        simo=simo,
                        verbose=verbose,
                        smooth=smooth_output,
                        vfoHost=vfo_host,
                        normalize=normalize_input)

        for proc in processes:
            proc.start()
            tprint(f'Started proc {proc.name}: {proc.pid}')

        tprint(f'Started proc Main: {getpid()}')
        eprint(repr(IOArgs.strct['processor']))
        readFile(swapEndianness=swap_input_endianness,
                 **{**ioArgs.strct, **ioArgs.strct['fileInfo']})

        for proc in processes:
            proc.join()
            vprint(f'{proc.name} returned: {proc.exitcode}')
    except KeyboardInterrupt:
        pass
    except ValueError as ex:
        if 'is closed' not in str(ex):
            printException(ex)
    except (BaseException, Exception) as ex:
        printException(ex)
    finally:
        __stopProcessing()
        for buffer, proc in zip(buffers, processes):
            tprint(f'Closing buffer {buffer}')
            buffer.close()
            buffer.cancel_join_thread()
            tprint(f'Closed buffer {buffer}')
            proc.join(2)
            if proc.exitcode is None:
                tprint(f'Killing process {proc}')
                proc.kill()
                proc.join()
                vprint(f'{proc.name} returned: {proc.exitcode}')
            proc.close()
        vprint('Main halted')


def __setStartMethod():
    if 'spawn' in get_all_start_methods():
        try:
            from multiprocessing import set_start_method, get_context

            set_start_method('spawn')
        except Exception as e:
            printException(e)
            raise AttributeError(f'Setting start method to spawn failed')


def __generatePidFile(pid):
    try:
        from datetime import UTC

        iso = datetime.now(UTC)
    except ImportError:
        iso = datetime.utcnow()

    iso = sub(r'[:\-+T]', '', iso.isoformat(timespec='seconds'))
    tmpfile = path.join(gettempdir(), f'{iso}-sdrterm-{uuid4()}.pid')

    with open(tmpfile, "w+") as pidfile:
        pidfile.write(str(pid) + '\n')
    eprint(f'PID file is created: {pidfile.name}')

    def deletePidFile():
        tprint(f'Attempting to delete PID file')
        try:
            unlink(tmpfile)
            vprint(f'PID file: {tmpfile} deleted')
        except OSError:
            pass

    setSignalHandlers(pid, __stopProcessing)
    return deletePidFile


def __stopProcessing():
    tprint(f'Setting halt condition')
    isDead.value = 1
    tprint(f'Halt condition set')
    __deletePidFile()


if __name__ == '__main__':
    __setStartMethod()
    __deletePidFile = __generatePidFile(getpid())
    isDead = Value('b', 0)
    isDead.value = 0
    typerRun(main)
