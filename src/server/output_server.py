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
from contextlib import closing
from queue import Empty
from threading import Thread

from misc.general_util import applyIgnoreException, printException


# taken from https://stackoverflow.com/a/45690594
def findPort(host='localhost'):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((host, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


class OutputServer:
    BUF_SIZE = 128

    def __init__(self,
                 port: int,
                 # exitFlag: Value,
                 host='localhost',
                 serverhost='localhost',
                 serverport=findPort()):
        self.host = host
        self.port = port
        self.serverport = serverport
        self.serverhost = serverhost
        self.clients: multiprocessing.Queue = multiprocessing.Queue(maxsize=os.cpu_count())
        self.dataType = 'B'

    def close(self, exitFlag):
        if exitFlag.value:
            try:
                exitFlag.value = 1

                for i in range(self.clients.qsize()):
                    try:
                        cs = self.clients.get_nowait()
                        cs.shutdown(socket.SHUT_RDWR)
                        cs.close()
                    except Empty:
                        break
                    finally:
                        self.clients.close()
                        del self.clients
            except Exception as e:
                printException(e)

    def consume(self, rs, exitFlag):
        processingList = []
        ii = range(self.BUF_SIZE >> 2)
        try:
            data = bytearray()
            while not exitFlag.value:
                for _ in ii:
                    inp = rs.recv(8192)
                    if inp is None or not len(inp):
                        break
                    data.extend(inp)
                try:
                    while not exitFlag.value:
                        cs = self.clients.get_nowait()
                        try:
                            cs.sendall(data)
                            processingList.append(cs)
                        except (ConnectionAbortedError, BlockingIOError, ConnectionResetError, ConnectionAbortedError, EOFError, BrokenPipeError) as e:
                            applyIgnoreException(lambda: cs.shutdown(socket.SHUT_RDWR))
                            cs.close()
                            print(f'Client disconnected {e}')
                except Empty:
                    pass
                for c in processingList:
                    self.clients.put(c)

                processingList.clear()
                data.clear()
        except (EOFError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as ex:
            printException(ex)
        finally:
            self.close(exitFlag)
            print('Consumer halted')

    def listen(self, ss, isConnected, exitFlag):
        with isConnected:
            ss.bind((self.host, self.serverport))
            ss.listen(1)
            isConnected.notify()

        try:
            while not exitFlag.value:
                (cs, address) = ss.accept()
                cs.setblocking(False)
                print(f'Connection request from: {address}')
                self.clients.put(cs)
        except OSError:
            pass
        except Exception as ex:
            e = str(ex)
            if not ('An operation was attempted on something that is not a socket' in e):
                printException(ex)
        finally:
            self.close(exitFlag)
            print('Listener halted')

    def initServer(self, s, ss, isConnected, exitFlag):
        st = Thread(target=self.listen, args=(ss, isConnected, exitFlag))
        pt = Thread(target=self.consume, args=(s, exitFlag))
        return st, pt
