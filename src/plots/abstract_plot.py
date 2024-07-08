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
from abc import ABC, abstractmethod
from typing import Callable

from numpy import linspace, arange, ndarray, dtype, complex64, complex128, exp, pi

from dsp.data_processor import DataProcessor
from misc.general_util import vprint


def check_halt_condition(method: Callable[..., int]) -> Callable[..., int]:
    def decorator(self) -> any:
        if self.isDead.value:
            self.quit()
            return None
        return method(self)

    return decorator


class AbstractPlot(DataProcessor, ABC):
    from multiprocessing import Value, Queue

    # frameRate default: ~60 fps
    def __init__(self,
                 isDead: Value,
                 fs: int,
                 buffer: Queue,
                 frameRate: int = 17,
                 center: int = 0,
                 tuned: int = 0,
                 *args, **kwargs):
        if isDead is None:
            raise ValueError('MultiSpectrumAnalyzerPlot cannot be used without a halt condition: isDead')
        if fs is None:
            raise ValueError('MultiSpectrumAnalyzerPlot cannot be used without a sampling rate: fs')
        if buffer is None:
            raise ValueError('MultiSpectrumAnalyzerPlot cannot be used without a buffer')

        self._t = None
        self._shift = None
        self._y = None
        self._dt = None
        self._nyquistFs = None
        self._fs = None
        self.widgets = None
        self.timer = None
        self.axis = None
        self.window = None

        self.buffer = buffer
        self.isDead = isDead
        self.frameRate = frameRate
        self.offset = center
        self.tuned = tuned
        self.fs = fs
        self._omega = -2j * pi * (self.offset / self.fs)

    def _shiftFreq(self, y: ndarray[any, dtype[complex64 | complex128]]) -> None:
        if self._t is None:
            self._t = arange(len(y))
            self._shift = exp(self._omega * self._t)
        y[:] = y * self._shift

    def _setTicks(self, n, num=11):
        for widget, off in self.widgets:
            xr, _ = widget.viewRange()
            oldRange = linspace(-n + off, n + off, num)
            newRange = linspace(xr[0], xr[1], 11)
            ticks = [[(float(u), str(round((v + self.tuned) / 10E+5, 3))) for u, v in zip(oldRange, newRange)]]
            widget.getAxis('bottom').setTicks(ticks)

    def __del__(self):
        del self.isDead
        del self.frameRate
        del self.offset
        del self.tuned
        del self.fs

    @property
    def fs(self) -> int:
        return self._fs

    @fs.setter
    def fs(self, value) -> None:
        self._fs = value
        self._nyquistFs = value >> 1
        self._dt = 1 / value

    @fs.deleter
    def fs(self) -> None:
        del self._fs
        del self._nyquistFs
        del self._dt

    @property
    def nyquistFs(self) -> int:
        return self._nyquistFs

    @nyquistFs.setter
    def nyquistFs(self, value) -> None:
        raise NotImplementedError('Setting the nyquistFs directly is not supported. Set fs instead')

    @property
    def dt(self) -> float:
        return self._dt

    @dt.setter
    def dt(self, value) -> None:
        raise NotImplementedError('Setting the dt directly is not supported. Set fs instead')

    @check_halt_condition
    def receiveData(self) -> int | None:
        # set buffer initially
        if self._y is None:
            self._y = self.buffer.get()
        else:
            self._y[:] = self.buffer.get()

        # check for EOF
        if self._y is None or not len(self._y):
            self.quit()
            return None
        return len(self._y)

    @abstractmethod
    def update(self) -> None:
        pass

    def quit(self) -> None:
        from pyqtgraph.Qt.QtCore import QCoreApplication
        self.timer.stop()
        self.buffer.close()
        self.buffer.join_thread()
        QCoreApplication.quit()
        vprint(f'Quit {self.__class__.__name__}')

    @classmethod
    def processData(cls, isDead: Value, buffer: Queue, fs: int, *args, **kwargs) -> None:
        spec = None
        try:
            from pyqtgraph.Qt import QtWidgets
            spec = cls(fs=fs, buffer=buffer, isDead=isDead, *args, **kwargs)
            spec.window.resize(640, 480)
            spec.window.show()
            spec.axis.setLabel("Frequency", units="Hz", unitPrefix="M")
            QtWidgets.QApplication.instance().exec()
        except (RuntimeWarning, KeyboardInterrupt):
            pass
        finally:
            if spec is not None:
                spec.quit()

    def __str__(self):
        return self.__class__.__name__
