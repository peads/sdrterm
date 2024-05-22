import mmap
import os
import struct
import sys
from functools import partial
from multiprocessing import Pipe, Process, Value
from uuid import UUID

import numpy as np

from misc.general_util import applyIgnoreException, printException, tprint, vprint


def readFile(wordtype, fs: int, fullFileRead: bool, isDead: Value, pipes: dict[UUID, Pipe],
             processes: dict[UUID, Process], f: str, offset=0, readSize=8192):
    bitdepth, structtype = wordtype
    readSize <<= bitdepth
    # ((x Samples/sec) * (y bytes/Sample)) * (1/(2^b * y) 1/bytes) * z seconds == 2^(-b) * x * z == (x * z) >> b
    # e.g., (fs S/s * 0.5 s) >> b == fs >> (1 + b)
    bufSize = fs >> int(2 + np.log2(readSize))
    with open(f, 'rb') if f is not None else open(sys.stdin.fileno(), 'rb', closefd=False) as ff:
        tprint(f'{f} {ff}')
        if sys.stdin.fileno() == ff.fileno() or not fullFileRead:
            file = ff
        else:
            vprint('Reading full file to memory')
            if 'posix' not in os.name:
                file = mmap.mmap(ff.fileno(), 0, access=mmap.ACCESS_READ)
            else:
                file = mmap.mmap(ff.fileno(), 0, prot=mmap.PROT_READ)
                file.madvise(mmap.MADV_SEQUENTIAL)
            vprint(f'Read: {file.size()} bytes')

        if offset:
            file.seek(offset)  # skip the wav header(s)

        try:
            data = bytearray()
            while not isDead.value:
                for _ in range(bufSize):
                    y = file.read(readSize)
                    if len(y) < 1:
                        break
                    data.extend(y)

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
                data.clear()
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
