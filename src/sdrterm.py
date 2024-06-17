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
from multiprocessing import Value, get_all_start_methods, set_start_method
from typing import Annotated
from uuid import UUID

import typer

from misc.general_util import printException, vprint, eprint
from misc.io_args import IOArgs
from misc.read_file import readFile


def main(fs: Annotated[int, typer.Option('--sampling-rate', '--fs', show_default=False, help='Sampling frequency in Samples/s')] = None,
         center: Annotated[float, typer.Option('--center-frequency', '-c', help='Offset from tuned frequency in Hz')] = 0,
         inFile: Annotated[str, typer.Option('--input', '-i', show_default='stdin', help='Input device')] = None,
         outFile: Annotated[str, typer.Option('--output', '-o', show_default='stdout', help='Output device')] = None,
         pl: Annotated[str, typer.Option('--plot', help='1D-Comma-separated value of plot type(s)')] = None,
         dm: Annotated[str, typer.Option('--demod', help='Demodulation type')] = 'fm',
         tuned: Annotated[int, typer.Option('--tuned-frequency', '-t', help='Tuned frequency in Hz')] = None,
         vfos: Annotated[str, typer.Option(help='1D-Comma-separated value of offsets from center frequency to process in addition to center in Hz')] = None,
         dec: Annotated[int, typer.Option('--decimation', help='Decimation factor')] = 2,
         bits: Annotated[int, typer.Option('--bits-per-sample', '-b', help='Bits per sample (ignored if wav file)')] = None,
         enc:  Annotated[str, typer.Option('--encoding', '-e', help='Binary encoding (ignored if wav file)')] = None,
         normalize: Annotated[bool, typer.Option(help='Toggle normalizing input analytic signal')] = False,
         omegaOut: Annotated[int, typer.Option('--omega-out', '-m', help='Cutoff frequency in Hz')] = 12500,
         correct_iq: Annotated[bool, typer.Option(help='Toggle iq correction')] = False,
         simo: Annotated[bool, typer.Option(help='EXPERIMENTAL enable using sockets to output data processed from multiple channels specified by the vfos option')] = False,
         verbose: Annotated[bool, typer.Option('--verbose', '-v', help='Toggle verbose output')] = False,
         trace: Annotated[bool, typer.Option(help='Toggle extra verbose output')] = False,
         read_size: Annotated[int, typer.Option(help='Size in bytes read per iteration')] = 65536):

    processes: dict[UUID, any] = {}
    isDead = Value('b', 0)
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
                    bits=bits,
                    enc=enc,
                    normalize=normalize,
                    correctIq=correct_iq,
                    simo=simo,
                    verbose=verbose,
                    trace=trace,
                    readSize=read_size)
    try:
        for proc in processes.values():
            proc.start()

        vprint(IOArgs.processor)
        readFile(buffers=IOArgs.buffers,
                 isDead=isDead,
                 offset=ioArgs.fileInfo['dataOffset'],
                 wordtype=ioArgs.fileInfo['bitsPerSample'],
                 f=ioArgs.inFile)
    except KeyboardInterrupt:
        pass
    except Exception as ex:
        printException(ex)
    finally:
        isDead.value = 1
        for proc in processes.values():
            proc.join(1)
        for buffer in IOArgs.buffers:
            buffer.cancel_join_thread()
        eprint('Main halted')
        return


if __name__ == '__main__':
    if 'spawn' in get_all_start_methods():
        try:
            set_start_method('spawn', force=True)
        except RuntimeError as e:
            raise RuntimeWarning(f'Warning: Setting start method failed\n{e}')
    typer.run(main)
