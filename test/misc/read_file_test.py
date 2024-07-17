import pytest

from misc.read_file import readFile


def test_read_file():
    with pytest.raises(ValueError) as e:
        readFile()
    print(f'\n{e.value}')

# TODO more tests