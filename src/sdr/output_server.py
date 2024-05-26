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
from multiprocessing import Value
from queue import Empty
from threading import Thread, Barrier, BrokenBarrierError

from misc.general_util import applyIgnoreException, printException, vprint, eprint
from sdr.util import findPort


class Receiver(ABC):

    def __init__(self, receiver, barrier=Barrier(2)):
        self.receiver = receiver
        self._barrier = barrier

    @property
    def barrier(self):
        return self._barrier

    @barrier.setter
    def barrier(self, _):
        raise NotImplemented("Receiver does not allow setting barrier")

    @barrier.deleter
    def barrier(self):
        del self._barrier

    @abstractmethod
    def receive(self):
        pass


class OutputServer:

    def __init__(self,
                 host='localhost',
                 port=findPort()):
        self.host = host
        self.port = port
        self.clients: multiprocessing.Queue = multiprocessing.Queue(maxsize=os.cpu_count())

    def close(self, exitFlag: Value, isConnected: Barrier) -> None:
        isConnected.abort()
        if not exitFlag.value:
            exitFlag.value = 1
            try:
                for i in range(self.clients.qsize()):
                    try:
                        clientSckt = self.clients.get_nowait()
                        clientSckt.send(b'')
                        clientSckt.shutdown(socket.SHUT_RDWR)
                        clientSckt.close()
                    except Empty:
                        break
                self.clients.close()
                del self.clients
            except Exception as e:
                printException(e)

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
                            applyIgnoreException(lambda: clientSckt.shutdown(socket.SHUT_RDWR))
                            clientSckt.close()
                            eprint(f'Client disconnected {e}')
                except Empty:
                    pass
                for c in processingList:
                    self.clients.put(c)
                processingList.clear()
        except (EOFError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            printException(e)
        finally:
            self.close(exitFlag, recvSckt.barrier)
            print('Feeder halted')

    def listen(self, listenerSckt: socket.socket, isConnected: Barrier, exitFlag: Value) -> None:
        # with isConnected:
        listenerSckt.bind((self.host, self.port))
        listenerSckt.listen(1)

        try:
            with ThreadPoolExecutor(max_workers=isConnected.parties) as pool:
                while not exitFlag.value:
                    (clientSckt, address) = listenerSckt.accept()
                    vprint(f'Connection request from: {address}')
                    self.clients.put(clientSckt)
                    if not isConnected.broken:
                        pool.submit(isConnected.wait)
                pool.shutdown()
        except OSError:
            pass
        except Exception as ex:
            e = str(ex)
            if not ('An operation was attempted on something that is not a socket' in e):
                printException(ex)
        finally:
            self.close(exitFlag, isConnected)
            print('Listener halted')

    def initServer(self,
                   recvSckt: Receiver,
                   listenerSckt: socket.socket,
                   exitFlag: Value) -> (Thread, Thread):
        listenerThread = Thread(target=self.listen, args=(listenerSckt, recvSckt.barrier, exitFlag))
        feedThread = Thread(target=self.feed, args=(recvSckt, exitFlag))
        return listenerThread, feedThread
