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
from enum import Enum
from struct import unpack
from typing import Iterable

from numpy import dtype

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
    b = dtype('|b')
    B = dtype('|B')

    h = dtype('=h')
    H = dtype('=H')

    i = dtype('=i4')
    I = dtype('=u4')

    f = dtype('=f4')
    d = dtype('=f8')

    def __str__(self):
        return self.name

    @classmethod
    def fromWav(cls, bits: int, aFormat: Enum, bFormat: Enum, isRifx: bool) -> dtype:
        eight = {'S': cls.b, 'U': cls.B, 'None': cls.B}
        sixteen = {'S': cls.h, 'U': cls.H, 'None': cls.h}
        thirtytwo = {'S': cls.i, 'U': cls.I, 'None': cls.i}

        ret = None
        splt = aFormat.name.split('_')
        if WaveFormat.WAVE_FORMAT_IEEE_FLOAT == aFormat:
            if 32 == bits:
                ret = cls.f.value
            elif 64 == bits:
                ret = cls.d.value
        elif WaveFormat.WAVE_FORMAT_PCM == aFormat or WaveFormat.WAVE_FORMAT_EXTENSIBLE == aFormat:
            istZahl = None

            if bFormat is not None and bFormat in ExWaveFormat:
                splt = bFormat.name.split('_')
                istZahl = splt[1]

            if 8 == bits:
                ret = eight[str(istZahl)].value
            elif 16 == bits:
                ret = sixteen[str(istZahl)].value
            elif 32 == bits:
                ret = thirtytwo[str(istZahl)].value

        if ret is None:
            raise ValueError(f'Unsupported format: {bits}: {aFormat}')

        if not (isRifx or 'BE' == splt[2]):
            ret = ret.newbyteorder('<')
        else:
            ret = ret.newbyteorder('>')

        return ret


def parseRawType(file: str | None, fs: int, enc: str) -> dict:
    if fs is None or fs < 1 or enc is None:
        raise ValueError('Sampling rate, encoding type and bit-size are required for raw pcm input')
    fs = int(fs)
    dataType = DataType[enc].value
    if file is not None and ':' in file:
        dataType = dataType.newbyteorder('>')
    result = zipRet((0, 0, 0, fs, fs, 0, dataType))
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


def checkWavHeader(f, fs: int, enc: str) -> dict:
    if f is None or issubclass(type(f), str) and ':' in f:
        return parseRawType(f, fs, enc)

    with open(f, 'rb') as file:
        # derived from http://soundfile.sapp.org/doc/WaveFormat/ and https://bts.keep-cool.org/wiki/Specs/CodecsValues
        headerStr = '<IHHIIHH'
        if b'RIF' != file.read(3):
            if '.wav' in f:
                raise ValueError('Invalid: Expected raw pcm file, but got malformed RIFF header')
            return parseRawType(f, fs, enc)
        else:
            temp = file.read(1)
            if not (b'F' == temp or b'X' == temp):
                raise ValueError('Invalid: malformed RIFF header')
            elif b'X' == temp:
                headerStr = '>IHHIIHH'
        chunkSize, = unpack('<I', file.read(4))
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
               ) = unpack(headerStr, file.read(20))
        ret = zipRet(ret)
        subFormat = None

        if WaveFormat.WAVE_FORMAT_EXTENSIBLE.value == ret['audioFormat']:
            extraParamSize, = unpack('<H', file.read(2))
            subFormatOffset = extraParamSize - 16
            extraParams = unpack('<' + str(subFormatOffset) + 'B', file.read(subFormatOffset))
            subFormat, = unpack('<H', file.read(2))
            if b'\x00\x00\x00\x00\x10\x00\x80\x00\x00\xAA\x00\x38\x9B\x71' != file.read(14):
                raise ValueError('Invalid SubFormat GUID')
            subFormat = ExWaveFormat(subFormat)

        ret['bitsPerSample'] = DataType.fromWav(bitsPerSample, WaveFormat(ret['audioFormat']), subFormat,
                                                '>' in headerStr)
        ret['bitRate'] = (bitsPerSample * byteRate * blockAlign) >> 3

        off = -1
        temp = file.tell()
        while -1 == off:
            buf = file.read(100)
            off = buf.find(b'data')
        off += temp
        file.seek(0)
        buf = file.read(off + 4)
        assert b'data' == buf[-4:]
        ret['dataOffset'] = file.tell()
    return ret
