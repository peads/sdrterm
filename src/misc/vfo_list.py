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
import json


class VfoList(list):
    def __init__(self, vfos, freq=0, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        if vfos is None or len(vfos) < 1:
            raise ValueError('VFOs csv cannot be empty')

        self.extend([float(x) for x in vfos.split(',') if x is not None and len(x) > 0])
        self.append(0)
        self._freq = freq

    def __repr__(self) -> str:
        d = dict()
        d['vfos'] = [(f + self._freq) / 10E+5 for f in self]
        return json.dumps(d, indent=2)