import os

import pytest

from misc.io_args import IOArgs, DemodulationChoices, selectPlotType


def nullFindSpec(*_, **__):
    return None


@pytest.fixture(scope='function')
def osEnv():
    ret = os.environ.pop('DISPLAY') if 'DISPLAY' in os.environ else None
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

    if osEnv is not None:  # DO NOT REMOVE; it's to prevent github's containerized rigs from barfing during testing
        with pytest.raises(ValueError) as e:
            selectPlotType(DemodulationChoices.FM)
        print(f'\n{e.value}')
        os.environ['DISPLAY'] = osEnv

    import importlib.util as rscs
    ogFiles = rscs.find_spec
    rscs.find_spec = nullFindSpec
    assert selectPlotType(DemodulationChoices.FM) is None
    rscs.find_spec = ogFiles
