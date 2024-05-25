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
from multiprocessing import Value, Pipe
from queue import Empty
from threading import Condition, Thread

from misc.general_util import applyIgnoreException, printException, vprint, eprint
from sdr.util import findPort


class Receiver(ABC):

    def __init__(self, receiver):
        self.receiver = receiver

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

    def close(self, exitFlag: Value) -> None:
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
                                ConnectionAbortedError, EOFError, BrokenPipeError) as e:
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
            self.close(exitFlag)
            print('Feeder halted')

    def listen(self, listenerSckt: socket.socket, isConnected: Condition, exitFlag: Value) -> None:
        with isConnected:
            listenerSckt.bind((self.host, self.port))
            listenerSckt.listen(1)
            isConnected.notify()

        try:
            while not exitFlag.value:
                (clientSckt, address) = listenerSckt.accept()
                # cs.setblocking(False)
                vprint(f'Connection request from: {address}')
                self.clients.put(clientSckt)
        except OSError:
            pass
        except Exception as ex:
            e = str(ex)
            if not ('An operation was attempted on something that is not a socket' in e):
                printException(ex)
        finally:
            self.close(exitFlag)
            print('Listener halted')

    def initServer(self,
                   recvSckt: Receiver,
                   listenerSckt: socket.socket,
                   isConnected: Condition,
                   exitFlag: Value) -> (Thread, Thread):
        listenerThread = Thread(target=self.listen, args=(listenerSckt, isConnected, exitFlag))
        feedThread = Thread(target=self.feed, args=(recvSckt, exitFlag))
        return listenerThread, feedThread
