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
import struct
import sys
from functools import partial
from multiprocessing import Pipe, Process, Value
from uuid import UUID

from misc.general_util import applyIgnoreException, printException, tprint


def readFile(wordtype, fs: int, isDead: Value, pipes: dict[UUID, Pipe],
             processes: dict[UUID, Process], f: str, readSize, offset=0):

    bitdepth, structtype = wordtype

    with open(f, 'rb') if f is not None else open(sys.stdin.fileno(), 'rb', closefd=False) as file:
        tprint(f'{f} {file}')

        if offset:
            file.seek(offset)  # skip the wav header(s)

        try:
            while not isDead.value:
                data = file.read(readSize)
                if data is None or len(data) < 1:
                    isDead.value = 1
                else:
                    y = struct.unpack_from((len(data) >> bitdepth) * structtype, data)
                    for (uuid, (r, w)) in list(pipes.items()):
                        r.close()
                        try:
                            w.send(y)
                        except (OSError, BrokenPipeError, TypeError):
                            w.close()
                            if uuid in pipes.keys():
                                pipes.pop(uuid)
                            if uuid in processes.keys():
                                processes.pop(uuid)
                # data.clear()
        except (EOFError, KeyboardInterrupt, OSError):
            pass
        except Exception as e:
            printException(e)
        finally:
            file.close()
            for (uuid, (r, w)) in list(pipes.items()):
                applyIgnoreException(partial(w.send, b''))
                w.close()
            isDead.value = 1
            print(f'Reader halted')
