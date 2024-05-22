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
from queue import Empty
from threading import Condition, Thread
from multiprocessing import Value

from misc.general_util import applyIgnoreException, printException
from sdr.util import findPort


class OutputServer:
    BUF_SIZE = 128

    def __init__(self,
                 host='localhost',
                 port=findPort()):
        self.host = host
        self.port = port
        self.clients: multiprocessing.Queue = multiprocessing.Queue(maxsize=os.cpu_count())
        self.dataType = 'B'

    def close(self, exitFlag: Value) -> None:
        if exitFlag.value:
            try:
                exitFlag.value = 1

                for i in range(self.clients.qsize()):
                    try:
                        clientSckt = self.clients.get_nowait()
                        clientSckt.send(b'')
                        clientSckt.shutdown(socket.SHUT_RDWR)
                        clientSckt.close()
                    except Empty:
                        break
                    finally:
                        self.clients.close()
                        del self.clients
            except Exception as e:
                printException(e)

    def feedClients(self, recvSckt: socket.socket, exitFlag: Value) -> None:
        processingList = []
        ii = range(self.BUF_SIZE >> 2)
        try:
            data = bytearray()
            while not exitFlag.value:
                for _ in ii:
                    inp = recvSckt.recv(8192)
                    if inp is None or not len(inp):
                        break
                    data.extend(inp)
                try:
                    while not exitFlag.value:
                        clientSckt = self.clients.get_nowait()
                        try:
                            clientSckt.sendall(data)
                            processingList.append(clientSckt)
                        except (ConnectionAbortedError, BlockingIOError, ConnectionResetError,
                                ConnectionAbortedError, EOFError, BrokenPipeError) as e:
                            applyIgnoreException(lambda: clientSckt.shutdown(socket.SHUT_RDWR))
                            clientSckt.close()
                            print(f'Client disconnected {e}')
                except Empty:
                    pass
                for c in processingList:
                    self.clients.put(c)

                processingList.clear()
                data.clear()
        except (EOFError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            printException(e)
        finally:
            self.close(exitFlag)
            print('Consumer halted')

    def listen(self, serverSckt: socket.socket, isConnected: Condition, exitFlag: Value) -> None:
        with isConnected:
            serverSckt.bind((self.host, self.port))
            serverSckt.listen(1)
            isConnected.notify()

        try:
            while not exitFlag.value:
                (clientSckt, address) = serverSckt.accept()
                # cs.setblocking(False)
                print(f'Connection request from: {address}')
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
                   serverSckt: socket.socket,
                   listenerSckt: socket.socket,
                   isConnected: Condition,
                   exitFlag: Value) -> (Thread, Thread):
        st = Thread(target=self.listen, args=(listenerSckt, isConnected, exitFlag))
        pt = Thread(target=self.feedClients, args=(serverSckt, exitFlag))
        return st, pt
