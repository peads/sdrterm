import os
import signal as s
import struct
from functools import partial
from multiprocessing import Pool

from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, shiftFreq
from misc.general_util import applyIgnoreException, deinterleave, eprint, printException


class VfoProcessor(DspProcessor):

    def handleOutput(self, file, freq, y):
        y = shiftFreq(y, freq, self.decimatedFs)
        y = signal.sosfilt(self.sosIn, y)
        y = self.demod(y)
        y = applyFilters(y, self.outputFilters)
        return os.write(file, struct.pack(len(y) * 'd', *y))

    def processData(self, isDead, pipe, f) -> None:
        s.signal(s.SIGINT, s.SIG_IGN)  # https://stackoverflow.com/a/68695455/8372013
        if f is None or (isinstance(f, str)) and len(f) < 1 \
                or self.demod is None:
            raise ValueError('f is not defined')
        reader, writer = pipe
        n = len(self.vfos)

        namedPipes = []
        for i in range(n):
            name = "/tmp/pipe-" + str(i)
            os.mkfifo(name)
            namedPipes.append((name, open(name, 'wb', os.O_WRONLY | os.O_NONBLOCK)))

        try:
            with Pool(maxtasksperchild=128) as pool:
                results = []
                while not isDead.value:
                    writer.close()
                    y = reader.recv()
                    if y is None or len(y) < 1:
                        break
                    y = deinterleave(y)
                    if self.correctIq is not None:
                        y = self.correctIq.correctIq(y)
                    y = shiftFreq(y, self.centerFreq, self.fs)
                    y = signal.decimate(y, self.decimation, ftype='fir')
                    [r.get() for r in results]  # wait for any prior processing to complete
                    results = [pool.apply_async(self.handleOutput, (file.fileno(), freq, y),
                                                error_callback=eprint) for
                               (name, file), freq in zip(namedPipes, self.vfos)]
        except (EOFError, KeyboardInterrupt, BrokenPipeError):
            pass
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            pool.close()
            pool.join()
            del pool
            for n, fd in namedPipes:
                applyIgnoreException(partial(os.write, fd.fileno(), b''))
                applyIgnoreException(partial(os.close, fd.fileno()))
                os.unlink(n)
            reader.close()
            print(f'File writer halted')
