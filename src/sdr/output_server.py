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
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from multiprocessing import Value, Queue
from queue import Empty
from threading import Thread, Barrier, BrokenBarrierError

from misc.general_util import printException, eprint, shutdownSocket
from misc.hooked_thread import HookedThread
from sdr.receiver import remove_context, prevent_out_of_context_execution, Receiver


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost') -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class OutputServer:

    def __init__(self, exitFlag: Value, host: str = 'localhost', port: int = findPort()):
        self.host = host
        self.port = port
        self.clients: Queue = Queue(maxsize=os.cpu_count())
        self._inside_context = False
        self.exitFlag = exitFlag

    def __enter__(self):
        self._inside_context = True
        return self

    @remove_context
    def __exit__(self, *exc):
        self.exitFlag.value = 1
        while 1:
            try:
                clientSckt = self.clients.get_nowait()
                shutdownSocket(clientSckt)
            except FileNotFoundError:
                pass
            except (Empty, ValueError, OSError, TypeError):
                break
            except Exception as e:
                printException(e)
                break
        self.clients.close()
        self.clients.join_thread()

    @prevent_out_of_context_execution
    def feed(self, recvSckt: Receiver, exitFlag: Value) -> None:
        processingList = []
        try:
            while not exitFlag.value:
                y = recvSckt.receive()
                try:
                    while not exitFlag.value:
                        clientSckt = self.clients.get(timeout=0.01)
                        try:
                            clientSckt.sendall(y)
                            processingList.append(clientSckt)
                        except (ConnectionAbortedError, BlockingIOError, ConnectionResetError,
                                ConnectionAbortedError, EOFError, BrokenPipeError, BrokenBarrierError) as e:
                            shutdownSocket(clientSckt)
                            eprint(f'Client disconnected {e}')
                except Empty:
                    pass
                for c in processingList:
                    self.clients.put(c)
                processingList.clear()
        except (KeyboardInterrupt, ValueError, OSError, EOFError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            printException(e)
        finally:
            eprint('Feeder halted')
            return

    @prevent_out_of_context_execution
    def listen(self, listenerSckt: socket.socket, isConnected: Barrier, exitFlag: Value) -> None:
        listenerSckt.bind((self.host, self.port))
        listenerSckt.listen(1)

        try:
            with ThreadPoolExecutor(max_workers=isConnected.parties) as pool:
                while not exitFlag.value:
                    (clientSckt, address) = listenerSckt.accept()
                    eprint(f'Connection request from: {address}')
                    self.clients.put(clientSckt)
                    if not isConnected.broken:
                        pool.submit(isConnected.wait)
        except (OSError, KeyboardInterrupt):
            pass
        except Exception as e:
            printException(e)
        finally:
            eprint('Listener halted')
            return

    @prevent_out_of_context_execution
    def initServer(self,
                   recvSckt: Receiver,
                   listenerSckt: socket.socket,
                   exitFlag: Value) -> (Thread, Thread):
        listenerThread = HookedThread(exitFlag, name='Listener', target=self.listen,
                                      args=(listenerSckt, recvSckt.barrier, exitFlag))
        feedThread = HookedThread(exitFlag, target=self.feed, args=(recvSckt, exitFlag))
        return listenerThread, feedThread
