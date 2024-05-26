#!/usr/bin/env python3
#
# This file is part of the sdrterm distribution
# (https://github.com/peads/sdrterm).
# Copyright (c) 2023-2024 Patrick Eads.
# With code from the cariboulite distribution 
# (https://github.com/cariboulabs/cariboulite)
# Copyright (c) 2024 CaribouLabs.co
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
from ctypes import cdll, c_byte, c_int, create_string_buffer, Structure, pointer, c_bool, c_float, \
    c_size_t
from typing import Annotated

import typer


def main(force_program: Annotated[bool, typer.Option(help='Force re-programming of FPGA')] = False,
         verbose: Annotated[
             int, typer.Option('--verbose', '-v', help='Verbosity setting for libcaribou')] = 2):
    libcar = cdll.LoadLibrary("libcariboulite.so")

    hw_ver = c_byte(-1)
    hw_name = create_string_buffer(128)
    hw_uuid = create_string_buffer(128)

    detected = libcar.cariboulite_detect_connected_board(pointer(hw_ver), hw_name, hw_uuid)

    print(
        f'Detection: {detected}, HWVer: {hw_ver.value}, HWName: {hw_name.value},  UUID: {hw_uuid.value}')

    # typedef struct
    # {
    #     int major_version;
    #     int minor_version;
    #     int revision;
    # } cariboulite_lib_version_st;

    class cariboulite_lib_version_st(Structure):
        pass

    cariboulite_lib_version_st._fields_ = [('major_version', c_int), ('minor_version', c_int),
                                           ('revision', c_int)]
    version = cariboulite_lib_version_st()

    libcar.cariboulite_get_lib_version(pointer(version))

    print('Version: %02d.%02d.%02d' % (
    version.major_version, version.minor_version, version.revision))

    forceProgram = c_bool(force_program)
    verbosity = c_byte(verbose)
    libcar.cariboulite_init(forceProgram, verbosity)
    serial_number = libcar.cariboulite_get_sn()

    print('Serial Number: %08X' % (serial_number))

    ch_name = create_string_buffer(64)
    low_freq_vec = (c_float * 3)()
    high_freq_vec = (c_float * 3)()

    for ch in range(1):
        libcar.cariboulite_get_channel_name(c_int(ch), ch_name, c_size_t(len(ch_name)))
        ch_num_ranges = libcar.cariboulite_get_num_frequency_ranges(ch)
        print(f'Channel: %d, Name: %s, Num. Freq. Ranges: %d' % (ch, ch_name.value, ch_num_ranges))
        libcar.cariboulite_get_frequency_limits(ch, low_freq_vec, high_freq_vec, None)
        for i in range(ch_num_ranges):
            print(f'\tRange %d: [%.2f, %.2f]' % (i, low_freq_vec[i], high_freq_vec[i]))

    libcar.cariboulite_close()


if __name__ == "__main__":
    typer.run(main)
