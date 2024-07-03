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


class UnrecognizedInputError(Exception):
    def __init__(self, msg: str, e: Exception):
        super().__init__(f'{msg}, {e}')

class Controller(ABC):
    def __init__(self, connection):
        self.connection = connection

    @abstractmethod
    def setParam(self, command, param):
        pass

    @abstractmethod
    def setFrequency(self, freq):
        pass

    @abstractmethod
    def setFs(self, fs):
        pass