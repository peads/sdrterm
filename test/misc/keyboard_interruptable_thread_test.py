from threading import Event

import pytest

from misc.keyboard_interruptable_thread import KeyboardInterruptableThread


def test_keyboard_interruptable_thread():
    event = Event()

    def func():
        event.set()

    def target():
        raise KeyboardInterrupt

    thread = KeyboardInterruptableThread(func=func, target=target, name='Catches KeyboardInterrupt')
    thread.start()

    assert event.wait()
    thread.join()
    assert not thread.is_alive()
    print(f'\n{thread}')

    thread = KeyboardInterruptableThread(func=target, target=target, name='Catches Nested KeyboardInterrupt')
    thread.start()
    thread.join()
    assert not thread.is_alive()
    print(f'{thread}')

    def target():
        raise ValueError('Idk what else to put.')

    event.clear()
    thread = KeyboardInterruptableThread(func=func, target=target, name='Catches ValueError')
    thread.start()

    assert event.wait()
    thread.join()
    assert not thread.is_alive()
    print(f'{thread}')

    event.clear()
    thread = KeyboardInterruptableThread(func=target, target=target, name='Catches Nested ValueError')
    thread.start()

    thread.join()
    assert not thread.is_alive()
    print(f'{thread}')

    with pytest.raises(ValueError) as e:
        KeyboardInterruptableThread(func=None, target=target)
    print(f'{e.type.__name__}: {e.value}')
