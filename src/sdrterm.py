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
from enum import Enum
from typing import Annotated

from click import BadParameter
from typer import run, Option

from misc.file_util import DataType


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
            N.B. unlike normal mode, which uses the system-default endianness for output, the sockets output 
            network-default, big-endian bytes. Enable using sockets to output data processed from multiple channels
            specified by the vfos option. [Implies: --vfos <csv>]''')] = False,
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
                                                       show_default='False => network-default, big-endian')] = False):
    import os
    import tempfile
    from multiprocessing import Value, Process

    from misc.general_util import printException, vprint, eprint, tprint
    from misc.io_args import IOArgs
    from misc.read_file import readFile

    from uuid import uuid4

    processes: list[Process] = []
    isDead = Value('b', 0)
    tmpfile = os.path.join(tempfile.gettempdir(), f'sdrterm-{uuid4()}.pid')
    with open(tmpfile, "w+") as pidfile:
        pidfile.write(str(os.getpid()))

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
                        pl=plot,
                        isDead=isDead,
                        omegaOut=omegaOut,
                        enc=enc,
                        correctIq=correct_iq,
                        simo=simo,
                        verbose=verbose,
                        smooth=smooth_output,
                        vfoHost=vfo_host)

        vprint(f'PID file is created: {pidfile}')
        for proc in processes:
            proc.start()

        eprint(IOArgs.strct['processor'])
        readFile(offset=ioArgs.strct['fileInfo']['dataOffset'],
                 wordtype=ioArgs.strct['fileInfo']['bitsPerSample'],
                 swapEndianness=swap_input_endianness, **ioArgs.strct)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        printException(ex)
    finally:
        for buffer, proc in zip(IOArgs.strct['buffers'], processes):
            tprint(f'Closing buffer {buffer}')
            buffer.cancel_join_thread()
            buffer.close()
            tprint(f'Closed buffer {buffer}')
            tprint(f'Awaiting {proc}')
            proc.join()
            tprint(f'{proc} completed')
            if proc.exitcode is None:
                vprint('Killing process {proc}')
                proc.kill()
                eprint('Killing process {proc}')
        isDead.value = 1
        os.unlink(tmpfile)
        vprint('Main halted')
        return


if __name__ == '__main__':
    from multiprocessing import get_all_start_methods, set_start_method

    if 'spawn' in get_all_start_methods():
        try:
            set_start_method('spawn', force=True)
        except RuntimeError as e:
            raise RuntimeWarning(f'Warning: Setting start method failed\n{e}')
    run(main)
