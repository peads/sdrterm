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
import multiprocessing
from abc import ABC, abstractmethod
from multiprocessing import Value, Queue
from typing import Iterable
from uuid import uuid4

import matplotlib as mpl
import matplotlib.style as mplstyle
import numpy as np
from matplotlib import pyplot as plt

from dsp.data_processor import DataProcessor
from dsp.iq_correction import IQCorrection
from dsp.util import shiftFreq
from misc.general_util import printException, eprint


class Plot(DataProcessor, ABC):
    def __init__(self, **kwargs):
        if 'fs' not in kwargs.keys() or not kwargs['fs']:
            raise ValueError('fs not specified')
        self.forPostProcessing = None
        self.bg = None
        self.ln = None
        self.ax = None
        self.fig = None
        self.isInit = False
        self.fs = kwargs['fs']
        self.centerFreq = kwargs['centerFreq'] if 'centerFreq' in kwargs.keys() and kwargs[
            'centerFreq'] is not None else 0
        self.bandwidth = (kwargs['bandwidth'] if 'bandwidth' in kwargs.keys() and kwargs[
            'bandwidth'] is not None else self.fs) / 2
        self.tunedFreq = kwargs['tunedFreq'] if 'tunedFreq' in kwargs.keys() and kwargs[
            'tunedFreq'] is not None else 0
        self.uuid = uuid4()
        self.vfos = kwargs['vfos'] if 'vfos' in kwargs.keys() and kwargs[
            'vfos'] is not None and len(kwargs['vfos']) > 1 else None
        if 'iq' in kwargs.keys() and kwargs['iq']:
            iqCorrector = IQCorrection(self.fs)
            self.correctIq = iqCorrector.correctIq
        self.processor = kwargs['processor'] if 'processor' in kwargs.keys() else None
        self.isRunning: bool = False

    def correctIq(self, x):
        return x

    @staticmethod
    def default_style(method):
        def decorator(self, *args, **kwargs):
            mpl.rcParams['toolbar'] = 'None'
            mplstyle.use('fast')

            return method(self, *args, **kwargs)

        return decorator

    @abstractmethod
    def animate(self, y: list | np.ndarray):
        pass

    @default_style
    @abstractmethod
    def initPlot(self, *args, **kwargs):
        pass

    def onClose(self, _):
        self.isRunning = False
        eprint(f'Window {type(self).__name__}: {self.fig}-{self.uuid} closed')

    def initBlit(self):
        plt.pause(0.1)
        isIterable = isinstance(self.ln, Iterable)
        self.bg = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        if self.ln is not None and not isIterable:
            self.ax.draw_artist(self.ln)
        if not isIterable:
            self.fig.canvas.blit(self.fig.bbox)
        self.fig.canvas.mpl_connect('close_event', self.onClose)
        self.isInit = True
        self.fig.canvas.manager.set_window_title(type(self).__name__)

    def processData(self, isDead: Value, buffer: Queue) -> None:
        self.isRunning = True
        try:
            while not isDead.value and self.isRunning:
                y = buffer.get()
                if y is None or not len(y):
                    break
                y = deinterleave(y)
                y = self.correctIq(y)
                y = shiftFreq(y, self.centerFreq, self.fs)
                self.animate(y)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            eprint(f'Process {multiprocessing.current_process().name} raised exception')
            printException(e)
        finally:
            buffer.close()
            buffer.cancel_join_thread()
            eprint(f'Figure {type(self).__name__}-{self.uuid} halted')
            return
