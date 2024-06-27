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
from typing import Annotated

import typer


def main(fs: Annotated[
    int, typer.Option('--fs', '-r', show_default=False, help='Sampling frequency in Samples/s')] = None,
         center: Annotated[
             float, typer.Option('--center-frequency', '-c', help='Offset from tuned frequency in Hz')] = 0,
         inFile: Annotated[str, typer.Option('--input', '-i', show_default='stdin', help='Input device')] = None,
         outFile: Annotated[str, typer.Option('--output', '-o', show_default='stdout', help='Output device')] = None,
         pl: Annotated[str, typer.Option('--plot', help='1D-Comma-separated value of plot type(s)')] = None,
         dm: Annotated[str, typer.Option('--demod', help='Demodulation type')] = 'fm',
         tuned: Annotated[int, typer.Option('--tuned-frequency', '-t', help='Tuned frequency in Hz')] = 0,
         vfos: Annotated[str, typer.Option(
             help='1D-Comma-separated value of offsets from center frequency to process in addition to center in Hz')] = None,
         dec: Annotated[int, typer.Option('--decimation', help='Decimation factor')] = 2,
         enc: Annotated[str, typer.Option('--encoding', '-e', help='Binary encoding (ignored if wav file)')] = None,
         omegaOut: Annotated[int, typer.Option('--omega-out', '-m', help='Output cutoff frequency in Hz')] = 12500,
         correct_iq: Annotated[bool, typer.Option(help='Toggle iq correction')] = False,
         simo: Annotated[bool, typer.Option(help='''
            N.B. unlike normal mode, which uses the system-default endianness for output, the sockets output 
            network-default, big-endian bytes. Enable using sockets to output data processed from multiple channels
            specified by the vfos option. [Implies: --vfos <csv>]''')] = False,
         verbose: Annotated[list[bool], typer.Option('--verbose', '-v',
                                                     help='Toggle verbose output. Repetition increases verbosity (e.g. -vv, or -v -v)')] = (),
         smooth_output: Annotated[int, typer.Option(
             help='Provide length of polynomial for smoothing output with Savitzky–Golay filter. More is more aggresive filtering.',
             show_default='0 => no filtering')] = 0,
         vfo_host: Annotated[
             str, typer.Option(help='Address on which to listen for vfo client connections')] = 'localhost',
         swap_input_endianness: Annotated[bool, typer.Option('--input-endianness', '-X',
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
                        dm=dm,
                        processes=processes,
                        pl=pl,
                        isDead=isDead,
                        omegaOut=omegaOut,
                        enc=enc,
                        correctIq=correct_iq,
                        simo=simo,
                        verbose=len(verbose) > 0,
                        trace=len(verbose) > 1,
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
    typer.run(main)
