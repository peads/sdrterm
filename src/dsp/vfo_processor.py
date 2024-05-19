import os
import struct
from multiprocessing import Pool

from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, cnormalize, convertDeinterlRealToComplex, shiftFreq
from misc.general_util import deinterleave, printException


class VfoProcessor(DspProcessor):

    def handleOutput(self, file, freq, y):
        y = shiftFreq(y, freq, self.decimatedFs)
        y = signal.sosfilt(self.sosIn, y)
        y = self.demod(y)
        y = applyFilters(y, self.outputFilters)
        return os.write(file, struct.pack(len(y) * 'd', *y))

    def processData(self, isDead, pipe, f) -> None:
        if f is None or (isinstance(f, str)) and len(f) < 1 \
                or self.demod is None:
            raise ValueError('f is not defined')
        reader, writer = pipe
        normalize = cnormalize if self.normalize else lambda x: x
        n = len(self.vfos)

        namedPipes = []
        for i in range(n):
            name = "/tmp/pipe-" + str(i)
            os.mkfifo(name)
            namedPipes.append((name, open(name, 'wb', os.O_WRONLY | os.O_NONBLOCK)))

        with Pool(processes=n) as pool:
            try:
                results = []
                while not isDead.value:
                    writer.close()
                    y = reader.recv()
                    if y is None or len(y) < 1:
                        break
                    y = deinterleave(y)
                    y = convertDeinterlRealToComplex(y)
                    y = normalize(y)
                    y = shiftFreq(y, self.centerFreq, self.fs)
                    y = signal.decimate(y, self.decimationFactor, ftype='fir')
                    [r.get() for r in results]  # wait for any prior processing to complete
                    results = [pool.apply_async(self.handleOutput, (file.fileno(), freq, y)) for (name, file), freq in zip(namedPipes, self.vfos)]

            except (EOFError, KeyboardInterrupt):
                isDead.value = 1
            except Exception as e:
                printException(e)
            finally:
                for n, fd in namedPipes:
                    os.close(fd.fileno())
                    os.unlink(n)
                reader.close()
                print(f'File writer halted')
