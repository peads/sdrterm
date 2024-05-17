import struct
from multiprocessing import Pipe, Process, Value
from uuid import UUID

from misc.general_util import eprint, printException


# def generateDomain(dataType: str):
#     xmin, xmax = None, None
#     match dataType:
#         case 'B':
#             xmin, xmax = 0, 255
#         case 'b':
#             xmin, xmax = -128, 127
#         case 'H':
#             xmin, xmax = 0, 65536
#         case 'h':
#             xmin, xmax = -32768, 32767
#         case 'I':
#             xmin, xmax = 0, 4294967295
#         case 'i':
#             xmin, xmax = -2147483648, 2147483647
#         case 'L':
#             xmin, xmax = 0, 18446744073709551615
#         case 'l':
#             xmin, xmax = -9223372036854775808, 9223372036854775807
#         case _:
#             pass
#     return xmin, xmax


def readFile(wordtype, isDead: Value, pipes: dict[UUID, Pipe],
             processes: dict[UUID, Process], f: str, offset=0, readSize=8192):
    MIN_BUF_SIZE = 16
    bitdepth, structtype = wordtype
    readSize <<= bitdepth
    with open(f, 'rb') as file:
        if offset:
            file.seek(offset)  # skip the wav header(s)
        try:
            # data = []
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
            isDead.value = 1
            eprint(f'Reader halted')
