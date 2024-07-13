import builtins
from io import BytesIO
from string import ascii_letters

import pytest
from numpy import dtype

from misc.file_util import checkWavHeader, DataType

builtinsOpen = builtins.open


@pytest.fixture(scope='function')
def uint8Header():
    """
    data produced via:
      echo "" | sox -traw -b8 -eunsigned-int -r8k - -twav /tmp/test.wav
      mediainfo test.wav
      General
      Complete name                            : test.wav
      Format                                   : Wave
      File size                                : 46.0 Bytes
      Overall bit rate mode                    : Constant

      Audio
      Format                                   : PCM
      Format settings                          : Unsigned
      Codec ID                                 : 1
      Bit rate mode                            : Constant
      Bit rate                                 : 64.0 kb/s
      Channel(s)                               : 1 channel
      Sampling rate                            : 8 000 Hz
      Bit depth                                : 8 bits
     printf "with open('/tmp/test.wav', 'rb') as f:\n\tprint(f.read())\n\n" | python
    """
    header = b'RIFF&\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00@\x1f\x00\x00\x01\x00\x08\x00data\x01\x00\x00\x00\n\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def int16Header():
    header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def int32Header():
    header = b'RIFFH\x00\x00\x00WAVEfmt (\x00\x00\x00\xfe\xff\x01\x00@\x1f\x00\x00\x00}\x00\x00\x04\x00 \x00\x16\x00 \x00\x04\x00\x00\x00\x01\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x008\x9bqfact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def float32Header():
    header = b'RIFF2\x00\x00\x00WAVEfmt \x12\x00\x00\x00\x03\x00\x01\x00@\x1f\x00\x00\x00}\x00\x00\x04\x00 \x00\x00\x00fact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def float64Header():
    header = b'RIFF2\x00\x00\x00WAVEfmt \x12\x00\x00\x00\x03\x00\x01\x00@\x1f\x00\x00\x00\xfa\x00\x00\x08\x00@\x00\x00\x00fact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def bigendianHeader():
    header = b'RIFX\x00\x00\x002WAVEfmt \x00\x00\x00\x12\x00\x03\x00\x01\x00\x00\x1f@\x00\x00\xfa\x00\x00\x08\x00@\x00\x00fact\x00\x00\x00\x04\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def twoChannelHeader():
    header = b'RIFF2\x00\x00\x00WAVEfmt \x12\x00\x00\x00\x03\x00\x02\x00@\x1f\x00\x00\x00\xf4\x01\x00\x10\x00@\x00\x00\x00fact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def rawHeader():
    header = b'\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader():
    header = b'RIFA2\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader2():
    header = b'RIFF2\x00\x00\x00AVI\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader3():
    header = b'RIFF2\x00\x00\x00WAVEtmf \x12'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader4():
    header = b'ASDF2\x00\x00\x00WAVEfmt \x12'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader5():
    header = b'RIFFH\x00\x00\x00WAVEfmt (\x00\x00\x00\xfe\xff\x01\x00@\x1f\x00\x00\x00}\x00\x00\x04\x00 \x00\x16\x00 \x00\x04\x00\x00\x00\x01\x00\x00\x00\x00\x00\x10\x00\x80\x00\x00\xaa\x008\x9bf'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badHeader6():
    header = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x11\x00data'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def badFloatBitRateHeader():
    header = b'RIFF2\x00\x00\x00WAVEfmt \x12\x00\x00\x00\x03\x00\x01\x00@\x1f\x00\x00\x00\xfa\x00\x00\x08\x00\x41\x00\x00\x00fact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(scope='function')
def alawHeader():
    header = b'RIFF2\x00\x00\x00WAVEfmt \x12\x00\x00\x00\x06\x00\x02\x00@\x1f\x00\x00\x80>\x00\x00\x02\x00\x08\x00\x00\x00fact\x04\x00\x00\x00\x00\x00\x00\x00data\x00\x00\x00\x00'
    ret = BytesIO(initial_bytes=header)
    builtins.open = lambda *_, **__: ret
    return ret


@pytest.fixture(autouse=True)
def cleanUp():
    builtins.open = builtinsOpen
    assert builtins.open == builtinsOpen
    yield
    builtins.open = builtinsOpen
    assert builtins.open == builtinsOpen


def test_checkUint8Header(uint8Header):
    ret = checkWavHeader(uint8Header, 0, '')
    assert ret is not None
    assert dtype('uint8') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkInt16Header(int16Header):
    ret = checkWavHeader(int16Header, 0, '')
    assert ret is not None
    assert dtype('int16') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkInt32Header(int32Header):
    ret = checkWavHeader(int32Header, 0, '')
    assert ret is not None
    assert dtype('int32') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkFloat32Header(float32Header):
    ret = checkWavHeader(float32Header, 0, '')
    assert ret is not None
    assert dtype('float32') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkFloat64Header(float64Header):
    ret = checkWavHeader(float64Header, 0, '')
    assert ret is not None
    assert dtype('float64') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkBigendianHeader(bigendianHeader):
    ret = checkWavHeader(bigendianHeader, 0, '')
    assert ret is not None
    assert dtype('>f8') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkTwoChannelHeader(twoChannelHeader):
    ret = checkWavHeader(twoChannelHeader, 0, '')
    assert ret is not None
    assert 2 == ret['numChannels']
    assert dtype('<f8') == ret['bitsPerSample']
    assert 8000 == ret['sampRate']


def test_checkRawHappyPath(rawHeader):
    def checkRawHappyPath():
        for f, enc in zip(('localhost:1234', None, rawHeader), ('b', 'B', 'h', 'H', 'i', 'I', 'f', 'd')):
            ret = checkWavHeader(f, 8000, enc)
            assert ret is not None
            expectedDataType = DataType[enc]
            str(expectedDataType)
            expectedDataType = expectedDataType.value
            assert expectedDataType == ret['bitsPerSample']
            assert 8000 == ret['sampRate']

    checkRawHappyPath()


def test_checkRawUnhappyPath():
    for f in ('', b''):
        with pytest.raises(FileNotFoundError):
            checkWavHeader(f, 8000, 'B')

    for ch in tuple(filter(lambda i: i not in ('b', 'B', 'h', 'H', 'i', 'I', 'f', 'd'), {*ascii_letters})):
        with pytest.raises(KeyError):
            checkWavHeader(None, 8000, ch)

    for fs in (-1, 0, None):
        with pytest.raises(ValueError):
            checkWavHeader(None, fs, 'B')

    with pytest.raises(TypeError):
        checkWavHeader(None, '2', 'B')


def test_checkBadHeader(badHeader):
    with pytest.raises(ValueError):
        checkWavHeader(badHeader, 8000, 'B')


def test_checkBadHeader2(badHeader2):
    with pytest.raises(ValueError):
        checkWavHeader(badHeader2, 8001, 'B')


def test_checkBadHeader3(badHeader3):
    with pytest.raises(ValueError):
        checkWavHeader(badHeader3, 8002, 'B')


def test_checkBadHeader4(badHeader4):
    with pytest.raises(ValueError):
        checkWavHeader("foo.wav", 8003, 'B')


def test_checkBadHeader5(badHeader5):
    with pytest.raises(ValueError):
        checkWavHeader(badHeader5, 8004, 'B')


def test_checkBadHeader6(badHeader6):
    with pytest.raises(ValueError):
        checkWavHeader(badHeader6, 8005, 'B')


def test_checkFloatBitRateHeader(badFloatBitRateHeader):
    with pytest.raises(ValueError):
        checkWavHeader(badFloatBitRateHeader, 8006, 'B')
        

def test_checkAlawHeader(alawHeader):
    with pytest.raises(ValueError):
        checkWavHeader(alawHeader, 8000, 'B')
