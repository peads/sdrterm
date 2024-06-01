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
import multiprocessing
import os
import socket
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Value, Queue
from queue import Empty
from threading import Thread, Barrier, BrokenBarrierError

from misc.general_util import printException, eprint, prevent_out_of_context_execution, \
    remove_context, closeSocket
from misc.hooked_thread import HookedThread
from sdr.util import findPort


class Receiver(ABC):

    def __init__(self, receiver, barrier=Barrier(2)):
        self._receiver = receiver
        self._barrier = barrier
        self._inside_context = False

    def __enter__(self):
        self._inside_context = True
        return self

    @remove_context
    @abstractmethod
    def __exit__(self, *exc):
        pass

    @property
    @prevent_out_of_context_execution
    def barrier(self):
        return self._barrier

    @barrier.setter
    @prevent_out_of_context_execution
    def barrier(self, _):
        raise NotImplemented("Receiver does not allow setting barrier")

    @barrier.deleter
    @prevent_out_of_context_execution
    def barrier(self):
        del self._barrier

    @property
    @prevent_out_of_context_execution
    def receiver(self):
        return self._receiver

    @receiver.setter
    @prevent_out_of_context_execution
    def receiver(self, _):
        raise NotImplemented("Receiver does not allow setting barrier")

    @receiver.deleter
    @prevent_out_of_context_execution
    def receiver(self):
        del self._receiver

    @abstractmethod
    @prevent_out_of_context_execution
    def receive(self):
        pass


class OutputServer:

    def __init__(self, exitFlag: Value, host='localhost', port=findPort()):
        self.host = host
        self.port = port
        self.clients: Queue = multiprocessing.Queue(maxsize=os.cpu_count())
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
                closeSocket(clientSckt)
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
                try:
                    while not exitFlag.value:
                        clientSckt = self.clients.get_nowait()
                        try:
                            clientSckt.sendall(recvSckt.receive())
                            processingList.append(clientSckt)
                        except (ConnectionAbortedError, BlockingIOError, ConnectionResetError,
                                ConnectionAbortedError, EOFError, BrokenPipeError, BrokenBarrierError) as e:
                            closeSocket(clientSckt)
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
            print('Feeder halted')
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
        except Exception as ex:
            e = str(ex)
            if not ('An operation was attempted on something that is not a socket' in e):
                printException(ex)
        finally:
            print('Listener halted')
            return

    @prevent_out_of_context_execution
    def initServer(self,
                   recvSckt: Receiver,
                   listenerSckt: socket.socket,
                   exitFlag: Value) -> (Thread, Thread):
        listenerThread = HookedThread(exitFlag, name='Listener', target=self.listen, args=(listenerSckt, recvSckt.barrier, exitFlag))
        feedThread = HookedThread(exitFlag, target=self.feed, args=(recvSckt, exitFlag))
        return listenerThread, feedThread
