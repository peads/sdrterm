from string import ascii_letters

import pytest

from misc.read_file import readFile, generateDomain

def test_read_file():
    with pytest.raises(ValueError) as e:
        readFile()
    print(f'\n{e.value}')
    
def test_generate_domain():
    chars = ('B', 'b', 'H', 'h', 'I', 'i', 'L', 'l')
    vals = (0, 255, -128, 127, 0, 65536, -32768, 32767, 0, 4294967295, -2147483648, 2147483647,
            0, 18446744073709551615, -9223372036854775808, 9223372036854775807)
    for c, (a, b) in zip(chars, [(vals[i],vals[i+1]) for i in range(0, len(vals), 2)]):
        xmin, diff = generateDomain(c)
        assert xmin == a
        assert diff == 1/(b-a)

    for c in tuple(filter(lambda i: i not in chars, {*ascii_letters})):
        domain = generateDomain(c)
        assert domain is None