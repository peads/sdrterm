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
import struct
from typing import Iterable

import numpy as np

from misc.general_util import vprint

WAVE_FORMAT_PCM = 0x0001
WAVE_FORMAT_IEEE_FLOAT = 0x0003
WAVE_FORMAT_ALAW = 0x0006
WAVE_FORMAT_MULAW = 0x0007
WAVE_FORMAT_EXTENSIBLE = 0xFFFE
PCM_S_LE = 0x01  # b'x01'
PCM_S_BE = 0x02  # b'x02'
PCM_S_PDP = 0x03  # b'x03'
PCM_U_LE = 0x05  # b'x05'
PCM_U_BE = 0x06  # b'x06'
PCM_U_PDP = 0x07  # b'x07'
SIGNED = 0
UNSIGNED = 1
TYPES = dict(((8, ((SIGNED, 'b'), (UNSIGNED, 'B'))),
              (16, ((SIGNED, 'h'), (UNSIGNED, 'H'))),
              (32, ((SIGNED, 'i'), (UNSIGNED, 'I'), (WAVE_FORMAT_IEEE_FLOAT, 'f'))),
              (64, ((SIGNED, 'l'), (UNSIGNED, 'L'), (WAVE_FORMAT_IEEE_FLOAT, 'd')))))


def parseRawType(bits, enc, fs):
    if fs is None or fs < 1:
        raise ValueError('fs is required for raw input')
    fs = int(fs)
    if bits is None and enc is None:
        result = zipRet((0, 0, 0, fs, 0, 0, (3, 'd')))
        result['dataOffset'] = 0
        return result
    elif len(enc) < 2:
        bits = int(np.log2(int(bits)) - 3)
        result = zipRet((0, 0, 0, fs, 0, 0, (bits, enc)))
        result['dataOffset'] = 0
    else:
        splt = enc.split('-')

        match splt[0]:
            case 'unsigned':
                signedness = UNSIGNED
            case 'signed':
                signedness = SIGNED
            case _:
                signedness = 3
        bits = int(bits)
        result = (0, 0, 0, fs, 0, 0, (int(np.log2(int(bits)) - 3), dict(TYPES[bits])[signedness]))
        result = zipRet(result)

    result['dataOffset'] = 0
    return result


def zipRet(x: Iterable):
    val = dict(zip(("subchunk1Size",
                    "audioFormat",
                    "numChannels",
                    "sampRate",
                    "byteRate",
                    "blockAlign",
                    "bitsPerSample"), x))
    return val


def checkWavHeader(f, fs, bits, enc):
    if not f:
        return parseRawType(bits, enc, fs)

    with open(f, 'rb') as file:
        # derived from http://soundfile.sapp.org/doc/WaveFormat/ and https://bts.keep-cool.org/wiki/Specs/CodecsValues
        if b'RIFF' != file.read(4):
            return parseRawType(bits, enc, fs)
        chunkSize, = struct.unpack('<I', file.read(4))
        if b'WAVE' != file.read(4):
            raise ValueError('Invalid: not wave file')
        if b'fmt ' != file.read(4):  # 0x666D7420:  # fmt
            raise ValueError('Invalid: format section not found')

        # the rest is little-endian
        #      name             bytes
        ret = (subchunk1Size,   # 4
               audioFormat,     # 2
               numChannels,     # 2
               sampRate,        # 4
               byteRate,        # 4
               blockAlign,      # 2
               bitsPerSample,   # 2
                                # 20
               ) = struct.unpack('<IHHIIHH', file.read(20))
        ret = zipRet(ret)
        ret['bitsPerSample'] = dict(TYPES[bitsPerSample])
        ret['sampRate'] = (bitsPerSample * numChannels * sampRate) >> 3

        bitsPerSample = int(np.log2(bitsPerSample) - 3)
        if WAVE_FORMAT_EXTENSIBLE != ret['audioFormat']:
            ret['bitsPerSample'] = (bitsPerSample, ret['bitsPerSample'][ret['audioFormat']])
        else:
            extraParamSize, = struct.unpack('<H', file.read(2))

            extraParams = struct.unpack('<' + ('B' * (extraParamSize - 16)), file.read(extraParamSize - 16))
            subFormat, = struct.unpack('<H', file.read(2))

            if b'\x00\x00\x00\x00\x10\x00\x80\x00\x00\xAA\x00\x38\x9B\x71' != file.read(14):
                raise ValueError('Invalid SubFormat GUID')

            if subFormat == PCM_S_BE or subFormat == PCM_S_LE:
                ret['bitsPerSample'] = (bitsPerSample, ret['bitsPerSample'][SIGNED])
            elif subFormat == PCM_U_BE or subFormat == PCM_U_LE:
                ret['bitsPerSample'] = (bitsPerSample, ret['bitsPerSample'][UNSIGNED])
            elif subFormat == PCM_S_PDP or subFormat == PCM_U_PDP:
                raise ValueError('Invalid: middle-endian not supported')
            else:
                raise ValueError('Invalid: Unknown non-PCM format not supported')

        buf = b''
        off = 0
        # TODO replace this garbage
        while 1:
            buf += file.read(1)
            if len(buf) > 3 and buf[-4:] == b'data':  # 0x64617461:
                off = file.tell()
                break
        ret['dataOffset'] = off
    vprint(json.dumps(ret, indent=2))
    return ret

# TODO Possible heuristic to determine datatype for raw PCM input by determining angle between real and imag compnents
#   (should be +/-Pi/2 +/- EPSILON)
# LEN = 128
# TYPES =
#  dict(((1, ('b', 'B')), (2, ('h', 'H')), (4, ('i', 'I', 'f')), (8, ('l', 'L', 'd'))))
# TYPES = dict(((8, 'B'), (16, 'h'), (32, ('i', 'f')), (64, 'd')))
# EPSILON = 10E-9
#         if len(TYPES[bitdepth]):
#             return bitdepth, TYPES[bitdepth], fs
#
#         frame = file.readframes(LEN)
#         for b in TYPES[bitdepth]:
#             v = np.array(struct.unpack(b * LEN, frame))
#             x = v[0::2]
#             y = v[1::2]
#             if len(x) < len(y):
#                 x[-1] = 0
#             else:
#                 y[-1] = 0
#             z = x + 1j * y
#             z = 1 / np.abs(z)
#             x = np.arccos(x * z)
#             y = np.arcsin(y * z)
#             z = np.sum(x - y)
#             if z < EPSILON:
#                 break
# return bitdepth, b, fs