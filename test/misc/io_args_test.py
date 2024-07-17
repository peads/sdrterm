import os

import pytest

from misc.io_args import IOArgs, DemodulationChoices


@pytest.fixture(scope='function')
def osEnv():
    ret = os.environ.pop('DISPLAY')
    yield ret


def test_ioargs(osEnv):
    with pytest.raises(ValueError):
        IOArgs._initializeProcess(None, None, name='p008')

    IOArgs.strct = kwargs = {'simo': True,
                             'vfo_host': 'localhost:1234',
                             'inFile': '/mnt/d/uint8.wav',
                             'outFile': "/dev/null",
                             'omegaOut': 5000,
                             'tuned': 155685000,
                             'center': -350000,
                             'vfos': "0",
                             }
    IOArgs._initializeOutputHandlers(fs=1024000,
                                     dm=DemodulationChoices.FM,
                                     pl='ps',
                                     processes=[],
                                     buffers=[],
                                     **kwargs)
    os.environ['DISPLAY'] = osEnv
    # os.environ.pop('DISPLAY')
    # IOArgs._initializeOutputHandlers(fs=1024000,
    #                                  dm=DemodulationChoices.FM,
    #                                  processes=[],
    #                                  buffers=[],
    #                                  **kwargs)
