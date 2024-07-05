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

from misc.general_util import vprint


def check_halt_condition(method: Callable[[any], any]) -> Callable[[any], any]:
    def decorator(self) -> any:
        if self.isDead.value:
            return None
        return method(self)

    return decorator


class AbstractPlot(ABC):
    from multiprocessing import Value

    # frameRate default: ~60 fps
    def __init__(self,
                 isDead: Value,
                 fs: int,
                 frameRate: int = 17,
                 center: int = 0,
                 tuned: int = 0,
                 *args, **kwargs):
        self._dt = None
        self._nyquistFs = None
        self._fs = None
        self.widgets = None

        self.isDead = isDead
        self.frameRate = frameRate
        self.offset = center
        self.tuned = tuned
        self.fs = fs
        self._t = None
        self._omega = -2j * pi * (self.offset / self.fs)
        self._shift = None

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

    @abstractmethod
    @check_halt_condition
    def receiveData(self) -> tuple[int, any]:
        pass

    @abstractmethod
    def update(self) -> None:
        pass

    def quit(self) -> None:
        from pyqtgraph.Qt.QtCore import QCoreApplication
        QCoreApplication.quit()
        vprint(f'Quit {self.__class__.__name__}')

    def __str__(self):
        return self.__class__.__name__
