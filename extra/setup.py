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
import os

import numpy
from Cython.Build import cythonize
from Cython.Distutils import Extension
from setuptools import setup

extraLinkArgs = []
if 'posix' in os.name:
    extraCompileArgs = ['-Ofast', '-flto=auto', '-fuse-linker-plugin', #'-fopenmp',
                        '-DNPY_NO_DEPRECATED_API']
    # extraLinkArgs = ['-fopenmp']
else:
    extraCompileArgs = ['/DNPY_NO_DEPRECATED_API', '/O2', '/Oiy', '/Ob3', '/favor:INTEL64', '/options:strict',# '/openmp',
                        '/fp:fast', '/fp:except-', '/GL', '/Gw', '/jumptablerdata', '/MP', '/Qpar']

setup(ext_modules=cythonize([
    Extension('dsp.fast.iq_correction',
              sources=['src/iq_correction.pyx'],
              include_dirs=[
                  numpy.get_include(),
              ],
              extra_compile_args=extraCompileArgs,
              extra_link_args=extraLinkArgs
              )
],
    annotate=True,
    show_all_warnings=True,
    force=True,
    language_level="3")
)
