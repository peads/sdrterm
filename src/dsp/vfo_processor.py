import os
import signal as s
import socket
from contextlib import closing
from functools import partial
from multiprocessing import Pool, Pipe, Value, Condition

import numpy as np
from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, shiftFreq
from misc.general_util import deinterleave, eprint, printException
from sdr.output_server import OutputServer, Receiver


class PipeReceiver(Receiver):
    def __init__(self, pipe: Pipe):
        receiver, writer = pipe
        super().__init__(receiver)

    def receive(self):
        return self.receiver.recv()


class VfoProcessor(DspProcessor):

    def processVfoChunk(self, y, freq) -> np.ndarray[any, np.real]:
        y = shiftFreq(y, freq, self.decimatedFs)
        y = signal.sosfilt(self.sosIn, y)
        y = self.demod(y)
        return applyFilters(y, self.outputFilters)

    def processData(self, isDead: Value, pipe: Pipe, _) -> None:
        if 'posix' in os.name:
            s.signal(s.SIGINT, s.SIG_IGN)  # https://stackoverflow.com/a/68695455/8372013

        inReader, inWriter = pipe

        outReader, outWriter = outPipe = Pipe(False)
        pool = None
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listenerSckt:
                isConnected = Condition()
                server = OutputServer(host='0.0.0.0')

                with isConnected:
                    lt, ft = server.initServer(PipeReceiver(outPipe), listenerSckt, isConnected, isDead)
                    lt.start()
                    isConnected.wait()
                    ft.start()
                del isConnected

                with Pool() as pool:
                    eprint(f'\nAccepting connections on port {server.port}\n')
                    while not isDead.value:
                        inWriter.close()
                        y = inReader.recv()
                        if y is None or len(y) < 1:
                            break

                        y = deinterleave(y)
                        if self.correctIq is not None:
                            y = self.correctIq.correctIq(y)
                        y = shiftFreq(y, self.centerFreq, self.fs)

                        y = signal.decimate(y, self.decimation, ftype='fir')
                        results = pool.map_async(partial(self.processVfoChunk, y), self.vfos).get()
                        [outWriter.send(r) for r in results]  # wait for any prior processing to complete
                    pool.join()
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            pass
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            del pool
            inReader.close()
            outReader.close()
            outWriter.close()
            print(f'File writer halted')
