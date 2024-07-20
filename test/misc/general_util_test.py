import os
import signal
from multiprocessing import get_context, Value, Event

import pytest
from pytest_cov.embed import cleanup

from misc.general_util import setSignalHandlers, traceOn


def fail(isDead: Value):
    isDead.value = 1
    cleanup()


def target(pid: Value, event: Event, isDead: Value):
    setSignalHandlers(os.getpid(), lambda: fail(isDead))
    traceOn()
    pid.value = os.getpid()
    event.set()
    while not isDead.value:
        pass


@pytest.fixture(scope='function')
def context():
    ctx = get_context('spawn')
    return ctx, ctx.Value('B', 0), ctx.Event(), ctx.Value('L', 0)


@pytest.fixture(scope='function')
def signals():
    ret = [signal.SIGTERM, signal.SIGINT]
    if 'posix' not in os.name:
        ret.append(signal.SIGBREAK)
        ignoredSignals = ()
    else:
        ret.extend([signal.SIGABRT, signal.SIGQUIT, signal.SIGHUP, signal.SIGXCPU])
        ignoredSignals = (signal.SIGTSTP, signal.SIGTTIN, signal.SIGTTOU)
    return ret, ignoredSignals


def test_general_util(context, signals):
    print('\n')
    ctx, isDead, event, pid = context
    sigs, ignoredSignals = signals
    for x in sigs:
        isDead.value = 0
        thread = ctx.Process(target=target, args=(pid, event, isDead))
        thread.start()
        event.wait()
        print(f'Sending {signal.Signals(x).name} to {pid.value}')
        [os.kill(pid.value, x) for x in ignoredSignals]
        os.kill(pid.value, x)
        thread.join()
        if 'posix' in os.name:
            assert isDead.value
        else:
            assert x == thread.exitcode
        print(f'Sent {signal.Signals(x).name} to {pid.value}')
        del thread
        event.clear()


def test_general_util2(context, signals):
    if 'posix' not in os.name:
        return
    traceOn()
    print('\n')
    ctx, isDead, event, pid = context
    sigs, ignoredSignals = signals
    for x in sigs:
        setSignalHandlers(os.getpid(), lambda: fail(isDead))
        isDead.value = 0
        pid.value = os.getpid()
        [os.kill(pid.value, x) for x in ignoredSignals]
        print(f'Sending {signal.Signals(x).name} to {pid.value}')
        os.kill(pid.value, x)
        assert isDead.value
        print(f'Sent {signal.Signals(x).name} to {pid.value}')
