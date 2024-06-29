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
import sys
import threading
from typing import Callable

from misc.general_util import printException
from misc.hooked_thread import HookedThread


class KeyboardInterruptableThread(HookedThread):
    def __init__(self, func: Callable[[], None], *args, **kwargs):
        if func is None:
            raise ValueError("func cannot be None")
        super().__init__(*args, **kwargs)
        setattr(self, 'handleExceptionHook', func)

        def handleException(e, *argv):
            try:
                self.handleExceptionHook()
            except Exception as ex:
                printException(ex, f'{self.name} caught {ex} while handling {e}')

            if not issubclass(type(e), KeyboardInterrupt):
                printException(e, f'{self.name} caught {e}')
            else:
                sys.__excepthook__(e, *argv)
            return

        threading.excepthook = handleException

    def handleExceptionHook(self):
        pass
