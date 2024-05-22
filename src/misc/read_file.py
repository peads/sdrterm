import os
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
