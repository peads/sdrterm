#!/usr/bin/env python3
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
import socket
import socketserver
import struct
from multiprocessing import Value
from threading import Thread
from typing import Annotated

import numpy as np
import typer
from rich.console import RenderableType
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.reactive import reactive
from textual.validation import Function
from textual.widgets import Button, RichLog, Input, Select, Label, Switch
from textual_slider import Slider

from misc.general_util import shutdownSocket, eprint, printException
from sdr import output_server
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.rtl_tcp_commands import RtlTcpSamplingRate, RtlTcpCommands
from sdr.socket_receiver import SocketReceiver


class SdrControl(App):
    CSS_PATH = "sdrcontrol.tcss"
    offset = reactive(0)
    fs = reactive(0)
    gain = reactive(0)
    freq = reactive(0)
    host = reactive('')
    port = reactive(-1)

    def __init__(self,
                 rs: SocketReceiver,
                 srv: socketserver.TCPServer,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.i2cSckt = None
        self.receiver = rs
        self.server = srv
        self.controller = None
        self.prevGain = None
        self.host = rs.host
        self.port = rs.port
        self.thread = None

    def exit(self, *args, **kwargs) -> None:
        if self.receiver is not None:
            self.receiver.disconnect()
            self.receiver = None
        shutdownSocket(self.i2cSckt)
        super().exit(*args, **kwargs)
        if self.i2cSckt is not None:
            self.i2cSckt.close()
        if self.thread is not None:
            self.thread.join(5)

    def resetBuffers(self, _):
        pass

    @on(Button.Pressed, '#connector')
    def onConnectorPressed(self, event: Button.Pressed) -> None:
        button = self.query('Button#connector')
        inp = self.query('Input.source')

        if event.button.has_class('connect'):
            try:
                self.host = self.query_one('#host', Input).value
                self.host = self.host if self.host else 'localhost'
                portBox = self.query_one('#port', Input)
                port = portBox.value
                self.port = int(port) if port else 1234
                portBox.value = str(self.port)

                self.i2cSckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.i2cSckt.settimeout(10)
                self.i2cSckt.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

                self.thread = Thread(target=self.getI2c, args=(), daemon=True)
                self.thread.start()

                self.receiver.host = self.host
                self.receiver.port = self.port
                self.receiver.connect()
                button.remove_class('connect')
                button.add_class('disconnect')
                event.button.watch_variant('success', 'error')
                event.button.label = 'Disconnect'
                self.controller = ControlRtlTcp(self.receiver.receiver, self.resetBuffers)
                inp.set(disabled=True)

                fsList = self.query_one('#fs_list', Select)
                frequency = self.query_one('#frequency', Input)
                fs = fsList.value
                fs = fs if str(fs) != "Select.BLANK" else 1024000
                freq = frequency.value
                self.freq = int(freq) if freq else 100000000
                dagc = self.query_one('#dagc_switch', Switch).value
                dagc = dagc if dagc else 0

                self.controller.setFs(fs)
                self.controller.setFrequency(self.freq + self.offset)
                self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, dagc)

                fsList.value = fs
                frequency.value = freq
                result = f'Accepting connections on port {self.server.socket.getsockname()[1]}'
            except (OSError, ConnectionError, EOFError) as e:
                result = str(e)
        elif event.button.has_class('disconnect'):
            shutdownSocket(self.i2cSckt)
            self.i2cSckt.close()
            self.receiver.disconnect()
            self.thread.join(0.1)
            self.controller = None
            self.thread = None
            button.remove_class('disconnect')
            button.add_class('connect')
            event.button.watch_variant('error', 'success')
            event.button.label = 'Connect'
            inp.set(disabled=False)
            label = self.query_one('#gains_label', Label)
            label.update('')
            result = 'Disconnected'
        else:
            raise RuntimeWarning(f'Unexpected input {event.button}')
        self.print(result)

    @on(Select.Changed, '#fs_list')
    def onFsChanged(self, event: Select.Changed) -> None:
        self.fs = event.value if str(event.value) != "Select.BLANK" else 0
        nyquistFs = self.fs >> 1
        slider = self.query_one('#offset', Slider)
        slider.min = -nyquistFs
        slider.max = nyquistFs
        slider.value = 0
        slider.disabled = False
        if self.controller:
            self.controller.setFs(self.fs)

    @on(Button.Pressed, '#set_freq')
    def onFreqPressed(self, _: Button.Pressed) -> None:
        if self.controller:
            value = self.query_one('#frequency', Input).value
            self.freq = int(value) if value else 0
            self.controller.setFrequency(self.freq + self.offset)

    @on(Slider.Changed, '#offset')
    def onOffsetChanged(self, event: Slider.Changed) -> None:
        self.offset = event.value
        self.query_one('#offset_label', Label).update(str(self.offset))
        if self.controller:
            self.controller.setFrequency(self.freq + self.offset)

    @on(Slider.Changed, '#gains_slider')
    def onGainsChanged(self, event: Slider.Changed) -> None:
        if self.controller and not self.query_one('#agc_switch', Switch).value:
            label = self.query_one('#gains_label', Label)
            label.styles.color = 'red'
            self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, event.value)

    @on(Switch.Changed, '#agc_switch')
    def onAgcChanged(self, event: Switch.Changed) -> None:
        value = event.value
        if self.controller:
            self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE.value, 1 - value)

    @on(Switch.Changed, '#dagc_switch')
    def onDagcChanged(self, event: Switch.Changed) -> None:
        if self.controller:
            value = event.value
            self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, value)

    @staticmethod
    def print(content: RenderableType | object):
        eprint(content)

    def getI2c(self) -> None:
        try:
            self.i2cSckt.connect((self.host, self.port + 1))
            self.call_from_thread(self.print, 'Waiting for I2C connection')
            self.i2cSckt.recv(38)
            self.call_from_thread(self.print, 'Got I2C connection')

            debounceCnt = 0
            prevData = None
            while 1:
                d = self.i2cSckt.recv(38)[5:]
                data = struct.unpack('!' + str(len(d)) + 'B', d)
                lna = data[5] & 0x1F
                mix = data[7] & 0x1F
                gain = (lna & 0xF) + (mix & 0xF)
                if prevData is None or prevData[5:7] != d[5:7]:
                    label = self.query_one('#gains_label', Label)
                    label.styles.color = 'yellow'
                    self.call_from_thread(self.updateGain, gain, color='yellow')
                prevData = d
                lnaStatus = (lna & 0x10) >> 4
                # mixerStatus = (lna & 0x10) >> 4
                if debounceCnt < 5:
                    debounceCnt += 1
                else:
                    self.call_from_thread(self.updateGain, gain, lnaStatus)
                    debounceCnt = 0
                # self.call_from_thread(self.print, bin(int.from_bytes(d[0xA:], signed=False, byteorder='big')))
        except KeyboardInterrupt:
            pass
        except Exception as e:
            printException(e)
        finally:
            shutdownSocket(self.i2cSckt)
            self.i2cSckt.close()
            return

    def updateGain(self, gain: int, lnaStatus: int = None, color: str = 'green') -> None:
        if gain > 28:
            gain = 28
        self.gain = gain
        label = self.query_one('#gains_label', Label)
        ogLabelValue = label.renderable
        label.update(str(self.gain))

        if lnaStatus is not None:
            agc = self.query_one('#agc_switch', Switch)
            ogAgcValue = agc.value
            agc.value = 1 - lnaStatus

            slider = self.query_one('#gains_slider', Slider)
            # only force the slider to update on connection or lna change
            if ('' == ogLabelValue or ogAgcValue != agc) and self.gain != slider.value:
                slider.value = self.gain
            slider.disabled = agc.value
        label.styles.color = color

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label('Source')
            with Horizontal():
                yield Input(placeholder='localhost',
                            id='host',
                            classes='source',
                            valid_empty=True,
                            validators=[Function(self.isValidHost, "Please input valid host.")],
                            value=self.host)
                yield Input(placeholder='1234', id='port', classes='source', type='integer')
                yield Button('Connect', id='connector', classes='connect', variant='success')

            yield Label('Tuning')
            with Horizontal():
                yield Input(placeholder='100000000 Hz', id='frequency', classes='frequency', type='integer')
                yield Button('Set', id='set_freq', classes='frequency')

            with Horizontal():
                yield Label('Offset ')
                yield Label('None', id='offset_label')
            yield Slider(-12500, 12500, id='offset', disabled=True, value=0, step=12500)

            yield Label('Sampling Rate')
            yield Select(RtlTcpSamplingRate.tuples(), prompt='Rate', classes='fs', id='fs_list')

            yield Label('Gains')
            with Horizontal():
                with Vertical():
                    yield Center(Label('', id='gains_label'))
                    yield Center(Slider(0, 28, id='gains_slider'))
                with Vertical():
                    yield Center(Label('LNA'))
                    yield Center(Switch(id='agc_switch'))
                with Vertical():
                    yield Center(Label('VGA'))
                    yield Center(Switch(id='dagc_switch'))

        log = RichLog(highlight=True, max_lines=10)
        yield log
        setattr(SdrControl, 'print', log.write)
        setattr(output_server, 'log', log.write)

    @staticmethod
    def isValidHost(value: str) -> bool:
        length = len(value) if value else 0
        if length < 1:
            return True

        if '-' in value[0]:
            return False

        value = value[-1]
        if (value.isalpha()
                or value.isnumeric()
                or '-' in value
                or '.' in value):
            return True

        return False


def main(server_host: Annotated[str, typer.Option(help='Port of local distribution server')] = 'localhost') -> None:
    isDead = Value('b', 0)
    isDead.value = 0
    # socket.setdefaulttimeout(1)
    with SocketReceiver(isDead=isDead) as receiver:
        try:
            server, lt, ft, resetBuffers = output_server.initServer(receiver, isDead, server_host=server_host)
            app = SdrControl(receiver, server)

            def reset(fs: int):
                resetBuffers()
                receiver.reset(None if fs > receiver.BUF_SIZE else (1 << int(np.log2(fs))))

            setattr(app, 'resetBuffers', reset)
            ft.start()
            lt.start()
            app.run()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            printException(e)
        finally:
            isDead.value = 1
            server.shutdown()
            server.server_close()
            app.exit(return_code=0)
            lt.join(5)
            ft.join(5)

            eprint('UI halted')
            return


if __name__ == '__main__':
    typer.run(main)
