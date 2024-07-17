import os
import signal
from multiprocessing import get_context, Value, Event

import pytest

from misc.general_util import setSignalHandlers, traceOn


def fail(value: Value):
    value.value = 1


def target(pid: Value, event: Event, value: Value):
    setSignalHandlers(os.getpid(), lambda: fail(value))
    traceOn()
    pid.value = os.getpid()
    event.set()
    while not value.value:
        pass


@pytest.fixture(scope='function')
def context():
    ctx = get_context('spawn')
    return ctx, ctx.Value('B', 0), ctx.Event(), ctx.Value('L', 0)


def test_general_util(context):
    print('\n')
    ctx, value, event, pid = context
    for x in [signal.SIGINT, signal.SIGQUIT, signal.SIGHUP, signal.SIGTERM, signal.SIGXCPU, signal.SIGABRT, ]:
        thread = ctx.Process(target=target, args=(pid, event, value,))
        thread.start()
        event.wait()
        print(f'Sent {signal.Signals(x).name} to {pid.value}')
        [os.kill(pid.value, x) for x in (signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU)]
        os.kill(pid.value, x)
        [os.kill(pid.value, x) for x in (signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU)]
        thread.join()
        assert value.value
        del thread
        event.clear()
        value.value = 0


def test_general_util2(context):
    print('\n')
    value = context[1]
    setSignalHandlers(os.getpid(), lambda: fail(value))
    for x in [signal.SIGINT, signal.SIGQUIT, signal.SIGHUP, signal.SIGTERM, signal.SIGXCPU, signal.SIGABRT, ]:
        [os.kill(os.getpid(), x) for x in (signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU)]
        os.kill(os.getpid(), x)
        [os.kill(os.getpid(), x) for x in (signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU)]
        assert value.value
        value.value = 0
