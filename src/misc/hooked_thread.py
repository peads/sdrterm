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
from multiprocessing import Value
from threading import Thread

from misc.general_util import printException


class HookedThread(Thread):
    def __init__(self, isDead: Value, group=None, target=None, name=None,
                 args=(), daemon=None):
        super().__init__(group=group, target=target, name=name, daemon=daemon, args=args)
        def handleException(e, *argv):
            isDead.value = 1
            if issubclass(type(e), KeyboardInterrupt):
                sys.__excepthook__(e, *argv)
            printException(e)
            return
            # printException(exc_value)

        threading.excepthook = handleException
