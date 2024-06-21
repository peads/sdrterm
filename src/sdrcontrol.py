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
import os
import socket
import socketserver
from importlib.resources import files
from multiprocessing import Value, Process
from typing import Annotated

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
from plots.socket_spectrum_analyzer import SocketSpectrumAnalyzer
from sdr import output_server
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.controller import Controller
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
                 ctrl: Controller,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.receiver = rs
        self.server = srv
        self.controller = ctrl
        self.graphSckt = None
        self.graphProc = None
        self.prevGain = None
        self.host = rs.host
        self.port = rs.port

    def exit(self, *args, **kwargs) -> None:
        self.shutdownGraph()
        if self.receiver is not None:
            self.receiver.disconnect()
            self.receiver = None
        super().exit(*args, **kwargs)

    @on(Button.Pressed, '#connector')
    def onConnectorPressed(self, event: Button.Pressed) -> None:
        button = self.query('Button#connector')
        inp = self.query('Input.source')

        if event.button.has_class('connect'):
            try:
                self.host = self.query_one('#host', Input).value
                self.host = self.host if self.host else 'localhost'
                port = self.query_one('#port', Input).value
                self.port = int(port) if port else 1234

                self.receiver.host = self.host
                self.receiver.port = self.port
                self.receiver.connect()
                button.remove_class('connect')
                button.add_class('disconnect')
                event.button.watch_variant('success', 'error')
                event.button.label = 'Disconnect'
                self.controller = ControlRtlTcp(self.receiver.receiver)
                inp.set(disabled=True)

                gainsSlider = self.query_one('#gains_slider', Slider)
                fsList = self.query_one('#fs_list', Select)
                frequency = self.query_one('#frequency', Input)
                gain = gainsSlider.value
                gain = int(gain) if gain else 0
                fs = fsList.value
                fs = fs if str(fs) != "Select.BLANK" else 1024000
                freq = frequency.value
                self.freq = int(freq) if freq else 100000000
                agc = self.query_one('#agc_switch', Switch).value
                agc = agc if agc else 0
                dagc = self.query_one('#dagc_switch', Switch).value
                dagc = dagc if dagc else 0

                self.controller.setFs(fs)
                self.controller.setFrequency(self.freq + self.offset)
                self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE.value, 1 - agc)
                self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, dagc)
                self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, gain)

                gainsSlider.value = gain
                fsList.value = fs
                frequency.value = freq

                result = f'Accepting connections on port {self.server.socket.getsockname()[1]}'
            except (OSError, ConnectionError, EOFError) as e:
                result = str(e)
        elif event.button.has_class('disconnect'):
            self.receiver.disconnect()
            self.controller = None
            button.remove_class('disconnect')
            button.add_class('connect')
            event.button.watch_variant('error', 'success')
            event.button.label = 'Connect'
            inp.set(disabled=False)
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
        self.gain = event.value
        label = self.query_one('#gains_label', Label)
        label.update(str(self.gain))
        if self.controller and not self.query_one('#agc_switch', Switch).value:
            self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, self.gain)

    @on(Switch.Changed, '#agc_switch')
    def onAgcChanged(self, event: Switch.Changed) -> None:
        value = event.value
        slider = self.query('#gains_slider')
        slider.set(disabled=value)
        slider = slider.first()
        if value:
            self.prevGain = slider.value
            slider.value = 0
        else:
            slider.value = self.prevGain
            self.prevGain = None
        if self.controller:
            self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE.value, 1 - value)

    @on(Switch.Changed, '#dagc_switch')
    def onDagcChanged(self, event: Switch.Changed) -> None:
        if self.controller:
            value = event.value
            self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, value)

    def shutdownGraph(self):
        if not (self.graphSckt is None or self.graphProc is None):
            self.print('Shutting graph socket down')
            shutdownSocket(self.graphSckt)
            self.print('Shut graph socket down')

            self.print('Joining graph process')
            self.graphProc.join(1)

            exitCode = self.graphProc.exitcode
            if exitCode is None:
                self.graphProc.kill()
                self.print('Graph killed')
            else:
                self.graphProc.close()
                self.print('Joined graph process')

            self.graphSckt.close()
            self.print(f'Graph exitcode: {exitCode}')
        self.graphProc = None
        self.graphSckt = None

    @on(Switch.Changed, '#graph_switch')
    def onGraphChanged(self, event: Switch.Changed) -> None:
        self.shutdownGraph()
        if event.value:
            self.graphSckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.graphSckt.settimeout(1)
            self.graphSckt.connect(self.server.socket.getsockname())
            self.graphProc = Process(target=SocketSpectrumAnalyzer.start,
                                     args=(),
                                     kwargs={'fs': self.fs, 'sock': self.graphSckt},
                                     daemon=True)
            self.graphProc.start()

    @staticmethod
    def print(content: RenderableType | object):
        eprint(content)

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

                if self.host is not None and self.port > 0:
                    variant = 'error'
                    label = 'Disconnect'
                else:
                    variant = 'success'
                    label = 'Connect'

                port = str(self.port) if self.port > 0 else ''
                yield Input(placeholder='1234', id='port', classes='source', type='integer', value=port)
                yield Button(label, id='connector', classes='connect', variant=variant)

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

            if 'posix' not in os.name or 'DISPLAY' in os.environ:
                try:
                    files('pyqtgraph')
                    yield Center(Label('Spectrum Equalizer'))
                    yield Center(Switch(id='graph_switch'))
                except ModuleNotFoundError:
                    pass

            yield Label('Gains')
            with Horizontal():
                with Vertical():
                    yield Center(Label('', id='gains_label'))
                    yield Center(Slider(0, 28, id='gains_slider'))
                with Vertical():
                    yield Center(Label('VGA'))
                    yield Center(Switch(id='agc_switch'))
                with Vertical():
                    yield Center(Label('LNA'))
                    yield Center(Switch(id='dagc_switch'))

        log = RichLog(highlight=True)
        yield log
        setattr(SdrControl, 'print', log.write)
        setattr(output_server, 'log', log.write)

    def on_mount(self) -> None:
        label = self.query_one('#gains_label', Label)
        label.update(str(self.query_one('#gains_slider', Slider).value))

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


def main(host: Annotated[str, typer.Argument(help='Address of remote server')] = None,
         port: Annotated[int, typer.Argument(help='Port of remote server')] = -1) -> None:
    isDead = Value('b', 0)
    isDead.value = 0
    controller = None
    with SocketReceiver(isDead=isDead, host=host, port=port) as receiver:
        try:
            if host is not None and port > 0:
                receiver.connect()
                controller = ControlRtlTcp(receiver.receiver)
            server, lt, ft = output_server.initServer(receiver, isDead, host='0.0.0.0')
            app = SdrControl(receiver, server, controller)

            ft.start()
            lt.start()
            app.run()
        except (ConnectionError, EOFError, KeyboardInterrupt):
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
