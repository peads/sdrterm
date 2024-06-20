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


class DataProcessor(ABC):
    """
    Interface for data processors.
    """

    @abstractmethod
    def processData(self, *args, **kwargs) -> None:
        """Consumer that performs processing on data input via a pipe
            and optionally writes it to a file specified by a filename (f) until condition (isDead) is nonzero

            Parameters:
            isDead (Value): bool-like (uint8) indicating whether, or not processing should be halted
            pipe (Connection): Connection from which to receive data
            f (str): Filename to which data may be written (defaults to None)
            Returns:
            None

           """
        pass
