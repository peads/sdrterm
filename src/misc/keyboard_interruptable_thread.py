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
from threading import Thread
from typing import Callable


class KeyboardInterruptableThread(Thread):
    def __init__(self, func: Callable[[], None], target: Callable, group=None, name=None, args=(), daemon=None):
        if func is None:
            raise ValueError("func cannot be None")
        super().__init__(group=group, target=target, name=name, args=args, daemon=daemon)
        setattr(self, '_handleException', func)
        import threading
        threading.excepthook = self.handleException

    def _handleException(self):
        pass

    def handleException(self, e):
        from misc.general_util import tprint
        from sys import __excepthook__

        try:
            self._handleException()
        except Exception as ex:
            tprint(ex)
        except BaseException as ex:
            __excepthook__(type(ex), ex, ex.__traceback__)

        if issubclass(e.exc_type, KeyboardInterrupt):
            __excepthook__(e.exc_type, e.exc_value, e.exc_traceback)
        else:
            tprint(e.exc_value)
        return
