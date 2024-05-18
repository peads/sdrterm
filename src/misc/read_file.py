import mmap
import os
import struct
import sys
from functools import partial
from multiprocessing import Pipe, Process, Value
from uuid import UUID

from misc.general_util import applyIgnoreException, eprint, printException


def readFile(wordtype, fullFileRead: bool, isDead: Value, pipes: dict[UUID, Pipe],
             processes: dict[UUID, Process], f: str, offset=0, readSize=8192):
    MIN_BUF_SIZE = 16
    bitdepth, structtype = wordtype
    readSize <<= bitdepth
    with open(f, 'rb') as ff:
        if sys.stdin.fileno() == ff.fileno() or not fullFileRead:
            file = ff
        else:
            eprint('Reading full file to memory')
            if os.name != 'POSIX':
                file = mmap.mmap(ff.fileno(), 0, access=mmap.ACCESS_READ)
            else:
                file = mmap.mmap(ff.fileno(), 0, prot=mmap.PROT_READ)
                file.madvise(mmap.MADV_SEQUENTIAL)
            eprint(f'Read: {file.size()} bytes')

        if offset:
            file.seek(offset)  # skip the wav header(s)

        try:
            data = bytearray()
            while not isDead.value:
                for _ in range(MIN_BUF_SIZE):
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
            eprint(f'Reader halted')
