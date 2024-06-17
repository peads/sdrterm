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
from multiprocessing import Barrier


def prevent_out_of_context_execution(method):
    def decorator(self, *args, **kwargs):
        if not self._inside_context:
            raise AttributeError(f"{method.__name__} may only be invoked from inside context.")
        return method(self, *args, **kwargs)

    return decorator


def remove_context(method):
    def decorator(self, *args, **kwargs):
        self._inside_context = False
        if hasattr(self, '_barrier'):
            self._barrier.abort()
        return method(self, *args, **kwargs)

    return decorator


class Receiver(ABC):

    def __init__(self, receiver=None, barrier=Barrier(2)):
        self._inside_context = False
        self._receiver = self.receiver = receiver
        self._barrier = barrier

    def __enter__(self):
        self._inside_context = True
        return self

    @remove_context
    @abstractmethod
    def __exit__(self, *exc):
        pass

    @property
    @prevent_out_of_context_execution
    def barrier(self):
        return self._barrier

    @barrier.setter
    @prevent_out_of_context_execution
    def barrier(self, _):
        raise NotImplemented("Receiver does not allow setting barrier")

    @barrier.deleter
    @prevent_out_of_context_execution
    def barrier(self):
        del self._barrier

    @abstractmethod
    @prevent_out_of_context_execution
    def receive(self):
        pass
