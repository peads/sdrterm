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
import struct
from enum import Enum
from typing import Iterable

import numpy as np

from misc.general_util import tprint
from misc.mappable_enum import MappableEnum


class WaveFormat(Enum):
    WAVE_FORMAT_PCM = 0x0001  # , ('B','h','i')
    WAVE_FORMAT_IEEE_FLOAT = 0x0003  # , ('f', 'd')
    WAVE_FORMAT_ALAW = 0x0006
    WAVE_FORMAT_MULAW = 0x0007
    WAVE_FORMAT_EXTENSIBLE = 0xFFFE


class ExWaveFormat(Enum):
    PCM_S_LE = 0x01
    PCM_S_BE = 0x02
    # PCM_S_PDP = 0x03
    PCM_U_LE = 0x05
    PCM_U_BE = 0x06
    # PCM_U_PDP = 0x07


class DataType(MappableEnum):
    b = np.dtype('b')
    B = np.dtype('B')

    h = np.dtype('>h')
    H = np.dtype('>H')

    i = np.dtype('>i4')
    I = np.dtype('>u4')

    f = np.dtype('>f4')
    d = np.dtype('>f8')

    def __str__(self):
        return self.name

    @classmethod
    def fromWav(cls, bits: int, aFormat: Enum, bFormat: Enum):
        eight = {'S': cls.b, 'U': cls.B, 'None': cls.B}
        sixteen = {'S': cls.h, 'U': cls.H, 'None': cls.h}
        thirtytwo = {'S': cls.i, 'U': cls.I, 'None': cls.i}

        ret = None
        if WaveFormat.WAVE_FORMAT_IEEE_FLOAT == aFormat:
            if 32 == bits:
                ret = cls.f.value
            elif 64 == bits:
                ret = cls.d.value
        elif WaveFormat.WAVE_FORMAT_PCM == aFormat or WaveFormat.WAVE_FORMAT_EXTENSIBLE == aFormat:
            istZahl = None
            splt = aFormat.name.split('_')

            if bFormat is not None and bFormat in ExWaveFormat:
                splt = bFormat.name.split('_')
                istZahl = splt[1]

            if 8 == bits:
                ret = eight[str(istZahl)].value
            elif 16 == bits:
                ret = sixteen[str(istZahl)].value
            elif 32 == bits:
                ret = thirtytwo[str(istZahl)].value

            if 'BE' != splt[2]:
                ret = ret.newbyteorder('<')

        if ret is not None:
            return ret

        raise ValueError(f'Unsupported format: {bits}: {aFormat}')


def parseRawType(fs, enc):
    if fs is None or fs < 1 or enc is None:
        raise ValueError('Sampling rate, encoding type and bit-size are required for raw pcm input')
    fs = int(fs)
    result = zipRet((0, 0, 0, fs, fs, 0, DataType[enc].value))
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


def checkWavHeader(f, fs, enc):
    if not f:
        return parseRawType(fs, enc)

    with open(f, 'rb') as file:
        # derived from http://soundfile.sapp.org/doc/WaveFormat/ and https://bts.keep-cool.org/wiki/Specs/CodecsValues
        if b'RIFF' != file.read(4):
            return parseRawType(fs, enc)
        chunkSize, = struct.unpack('<I', file.read(4))
        if b'WAVE' != file.read(4):
            raise ValueError('Invalid: not wave file')
        if b'fmt ' != file.read(4):  # 0x666D7420:  # fmt
            raise ValueError('Invalid: format section not found')

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
        subFormat = None

        if WaveFormat.WAVE_FORMAT_EXTENSIBLE.value == ret['audioFormat']:
            extraParamSize, = struct.unpack('<H', file.read(2))
            subFormatOffset = extraParamSize - 16
            extraParams = struct.unpack('<' + str(subFormatOffset) + 'B', file.read(subFormatOffset))
            subFormat, = struct.unpack('<H', file.read(2))
            if b'\x00\x00\x00\x00\x10\x00\x80\x00\x00\xAA\x00\x38\x9B\x71' != file.read(14):
                raise ValueError('Invalid SubFormat GUID')
            subFormat = ExWaveFormat(subFormat)

        ret['bitsPerSample'] = DataType.fromWav(bitsPerSample, WaveFormat(ret['audioFormat']), subFormat)
        ret['bitRate'] = (bitsPerSample * byteRate * blockAlign) >> 3

        off = -1
        temp = file.tell()
        while -1 == off:
            buf = file.read(100)
            off = buf.find(b'data')
        off += temp
        file.seek(0)
        buf = file.read(off + 4)
        if buf[-4:] != b'data':
            raise ValueError('Invalid: could not find data section.')
        ret['dataOffset'] = file.tell()
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
