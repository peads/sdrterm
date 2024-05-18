import os
import struct
from multiprocessing import Pool

from scipy import signal

from dsp.dsp_processor import DspProcessor
from dsp.util import applyFilters, cnormalize, convertDeinterlRealToComplex, shiftFreq
from misc.general_util import deinterleave, eprint, printException


class VfoProcessor(DspProcessor):

    def handleOutput(self, file, freq, y):
        # with open(name, 'wb') as file:
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

        namedPipes = []
        for i in range(len(self.vfos)):
            # uid = uuid.uuid4()
            name = "/tmp/pipe-" + str(i)  # str(uid)
            os.mkfifo(name)
            namedPipes.append((name, open(name, 'wb', os.O_WRONLY | os.O_NONBLOCK)))

        with Pool(processes=len(self.vfos) - 1) as pool:
            try:
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
                    results = [pool.apply_async(self.handleOutput, (file.fileno(), freq, y)) for (name, file), freq in zip(namedPipes, self.vfos)]
                    # y = signal.sosfilt(self.sosIn, y)
                    # y = self.demod(y)
                    # y = applyFilters(y, self.outputFilters)
                    # file.write(struct.pack(len(y) * 'd', *y))
                    results = [r.get() for r in results]

            except (EOFError, KeyboardInterrupt):
                isDead.value = 1
            except Exception as e:
                printException(e)
            finally:
                for n, fd in namedPipes:
                    os.close(fd.fileno())
                    os.unlink(n)
                reader.close()
                eprint(f'File writer halted')
