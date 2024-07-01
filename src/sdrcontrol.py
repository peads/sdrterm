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
from functools import reduce
from multiprocessing import Value
from socketserver import TCPServer
from threading import Thread
from typing import Annotated

from numpy import base_repr
from rich.console import RenderableType
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.reactive import reactive
from textual.validation import Function, Number
from textual.widgets import Button, RichLog, Input, Select, Label, Switch
from textual_slider import Slider
from typer import Option, run as typerRun

from misc.general_util import shutdownSocket, eprint
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
    host = reactive(None)
    port = reactive(None)
    ppm = reactive(0)
    dagc = reactive(0)
    agc = reactive(0)
    post = reactive(0)

    def __init__(self,
                 rs: SocketReceiver,
                 srv: TCPServer,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.receiver = rs
        self.server = srv
        self.controller = ControlRtlTcp(self.receiver.receiver, self.resetBuffers)
        self.i2cSckt = None
        self.prevGain = None
        self.thread = None

    def exit(self, *args, **kwargs) -> None:
        if self.receiver is not None:
            self.receiver.disconnect()
            self.receiver = None
        if self.i2cSckt is not None:
            shutdownSocket(self.i2cSckt)
            self.i2cSckt.close()
            self.i2cSckt = None
        if self.receiver is not None:
            self.receiver.disconnect()
            self.receiver = None
        if self.thread is not None and self.thread.is_alive():
            self.thread.join(0.1)
            self.thread = None
        super().exit(*args, **kwargs)

    def resetBuffers(self, _):
        pass

    @on(Button.Pressed, '#connector')
    def onConnectorPressed(self, event: Button.Pressed) -> None:
        event.button.variant = 'warning'
        button = self.query_one('Button#connector', Button)
        inp = self.query('Input.source')
        isValid = reduce(lambda x, y: x and y and x.is_valid and y.is_valid, inp.nodes)

        if isValid and event.button.has_class('connect'):
            from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_KEEPALIVE
            try:
                inp.set(disabled=True)

                if self.i2cSckt is not None:
                    shutdownSocket(self.i2cSckt)
                    self.i2cSckt.close()
                self.i2cSckt = socket(AF_INET, SOCK_STREAM)
                self.i2cSckt.settimeout(10)
                self.i2cSckt.setsockopt(SOL_SOCKET, SO_KEEPALIVE, 1)
                self.thread = Thread(target=self.getI2c, args=(), daemon=True)

                self.receiver.host = self.host
                self.receiver.port = self.port
                self.receiver.connect()

                self.fs = self.fs if self.fs else 1024000
                self.freq = self.freq if self.freq else 100000000

                self.controller.connection = self.receiver.receiver
                self.controller.setFs(self.fs)
                self.controller.setFrequency(self.freq + self.offset)
                self.controller.setParam(RtlTcpCommands.SET_AGC_MODE, self.dagc)
                self.controller.setParam(RtlTcpCommands.REPORT_I2C_REGS, 1)
                self.thread.start()

                button.remove_class('connect')
                button.add_class('disconnect')
                # event.button.watch_variant('warning', 'error')
                event.button.label = 'Disconnect'
                result = f'Accepting connections on port {self.server.socket.getsockname()[1]}'
            except (OSError, ConnectionError, EOFError) as e:
                button.remove_class('disconnect')
                button.add_class('connect')
                # event.button.watch_variant('warning', 'success')
                event.button.label = 'Connect'
                inp.set(disabled=False)
                result = str(e)
        elif event.button.has_class('disconnect'):
            shutdownSocket(self.i2cSckt)
            self.i2cSckt.close()
            self.receiver.disconnect()
            self.thread.join(0.1)
            self.controller.connection = None
            self.thread = None
            self.i2cSckt = None
            button.remove_class('disconnect')
            button.add_class('connect')
            event.button.variant = 'success'
            # event.button.watch_variant('error', 'success')
            event.button.label = 'Connect'
            label = self.query_one('#gains_label', Label)
            label.update('')
            inp.set(disabled=False)
            result = 'Disconnected'
        else:
            self.log(f'Unexpected input {event.button}')
            return
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
        self.controller.setFs(self.fs)

    @on(Input.Changed, '#host')
    def onHostChanged(self, event: Input.Changed) -> None:
        self.host = event.value

    @on(Input.Changed, '#port')
    def onPortChanged(self, event: Input.Changed) -> None:
        value = event.value
        self.port = int(event.value) if value else None

    # @on(Input.Submitted, '.source')
    # def onSourceSubmitted(self, event: Input.Submitted) -> None:
    #     self.print(event.value)

    @on(Button.Pressed, '#set_freq')
    def onConnectPressed(self, _: Button.Pressed) -> None:
        value = self.query_one('#frequency', Input).value
        self.freq = int(value) if value else 0
        self.controller.setFrequency(self.freq + self.offset)

    @on(Input.Changed, '#frequency')
    def onFreqChanged(self, event: Input.Changed) -> None:
        value = int(event.value) if event.value else 0
        self.freq = value if value > 0 else 0

    @on(Slider.Changed, '#offset')
    def onOffsetChanged(self, event: Slider.Changed) -> None:
        self.offset = event.value
        self.query_one('#offset_label', Label).update(str(self.offset))
        self.controller.setFrequency(self.freq + self.offset)

    @on(Slider.Changed, '#gains_slider')
    def onGainsChanged(self, event: Slider.Changed) -> None:
        if self.i2cSckt is not None:
            label = self.query_one('#gains_label', Label)
            label.styles.color = 'red'
            self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX, event.value)

    @on(Switch.Changed, '#agc_switch')
    def onAgcChanged(self, event: Switch.Changed) -> None:
        self.agc = event.value
        self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE, 1 - self.agc)

    @on(Switch.Changed, '#dagc_switch')
    def onDagcChanged(self, event: Switch.Changed) -> None:
        self.dagc = event.value
        self.controller.setParam(RtlTcpCommands.SET_AGC_MODE, self.dagc)

    @staticmethod
    def print(content: RenderableType | object):
        eprint(content)

    def getI2c(self) -> None:
        try:
            from struct import unpack
            self.call_from_thread(self.print, 'Waiting for I2C connection')
            self.i2cSckt.connect((self.host, self.port + 1))
            d = self.i2cSckt.recv(38)[5:]
            self.call_from_thread(self.print, 'Got I2C connection')

            debounceCnt = 0
            prevData = None
            while 1:
                data = unpack('!' + str(len(d)) + 'B', d)
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
                    self.query_one("#connector").variant = 'error'
                    debounceCnt = 0
                d = self.i2cSckt.recv(38)[5:]

                # self.call_from_thread(self.print, hex(int.from_bytes(d[0x14:0x1C], signed=False, byteorder='big')))

                tmp = d[0x14] & 0x3F
                si2c = ((d[0x14] ) >> 6) & 3
                ni2c = (d[0x14] << 2) >> 2
                nfra = int.from_bytes(d[0x15:0x17], signed=False, byteorder="little")
                nint = (ni2c << 2) + si2c + 13
                nint2 = (tmp << 2) + si2c + 13
                ndiv = (nint + nfra) << 1
                ndiv2 = (nint2 + nfra) << 1
                self.call_from_thread(self.print, f'{si2c} : {ni2c} : {tmp} : {nint} : {nint2} : {d[0x15]} : {d[0x16]}  : {nfra} : {ndiv} : {ndiv2}')

        except KeyboardInterrupt:
            pass
        except Exception as e:
            self.log(e)
        finally:
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
                            validators=[Function(self.isValidHost, "Please input valid host.")],
                            valid_empty=False)
                yield Input(placeholder='1234',
                            id='port',
                            classes='source',
                            type='integer',
                            valid_empty=False)
                # validate_on=['submitted'])
                yield Button('Connect', id='connector', classes='sources connect', variant='success')

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
        if length < 1 or '-' in value[0]:
            return False

        value = value[-1]
        if (value.isalpha()
                or value.isnumeric()
                or '-' in value
                or '.' in value):
            return True

        return False


def main(server_host: Annotated[str, Option(help='Port of local distribution server')] = 'localhost') -> None:
    from os import getpid
    isDead = Value('b', 0)
    isDead.value = 0
    eprint(f'sdrcontrol pid: {getpid()}')

    with SocketReceiver(isDead=isDead) as receiver:
        try:
            from misc.general_util import setSignalHandlers
            server, lt, ft, resetBuffers = output_server.initServer(receiver, isDead, server_host=server_host)
            app = SdrControl(receiver, server)

            setattr(app, 'resetBuffers', resetBuffers)
            ft.start()
            lt.start()
            app.run()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            app.log(e)
        finally:
            isDead.value = 1
            server.shutdown()
            app.exit(return_code=0)
            # server.server_close()
            lt.join(5)
            ft.join(5)
            SdrControl.print('UI halted')
            return


if __name__ == '__main__':
    typerRun(main)
