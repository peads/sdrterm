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
from setuptools import setup, find_namespace_packages

setup(
    name='sdrterm',
    version='0.0.01',
    description='Provides simple terminal-based user-interface for processing/analysis of SDR data',
    url='https://github.com/peads/sdrterm',
    author='Patrick Eads',
    author_email='peads@users.noreply.github.com',
    license='GPLv3',
    package_dir={"": "src"},
    packages=find_namespace_packages(where='src'),
    # install_requires=['scipy',
    #                   'numpy',
    #                   'matplotlib',
    #                   'typer',
    #                   ],
    license_files=('LICENSE',),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Telecommunications Industry',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Environment :: Console',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows :: Windows 7',
        'Operating System :: Microsoft :: Windows :: Windows 8',
        'Operating System :: Microsoft :: Windows :: Windows 8.1',
        'Operating System :: Microsoft :: Windows :: Windows 10',
        'Operating System :: Microsoft :: Windows :: Windows 11',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio :: Analysis',
        'Topic :: Scientific/Engineering :: Physics',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: System :: Hardware :: Universal Serial Bus (USB) :: Audio',
        'Topic :: System :: Networking',
        'Topic :: Utilities',
        'Typing :: Typed'
    ],
)
