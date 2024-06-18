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
import sys
from importlib.resources import files
from multiprocessing import Value, Process

from rich.console import RenderableType
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Center
from textual.reactive import reactive
from textual.validation import Function
from textual.widgets import Button, RichLog, Input, Select, Label, Switch
from textual_slider import Slider

from misc.general_util import shutdownSocket, eprint
from plots.spectrum_analyzer import SpectrumAnalyzer
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

    def __init__(self,
                 rs: socket,
                 srv: socketserver.TCPServer,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.recvSckt = rs
        self.server = srv
        self.graphSckt = None
        self.controller = None
        self.graphProc = None
        self.prevGain = None

    @on(Button.Pressed, '#connector')
    def onConnectorPressed(self, event: Button.Pressed) -> None:
        button = self.query('Button#connector')
        inp = self.query('Input.source')

        if event.button.has_class('connect'):
            try:
                host = self.query_one('#host', Input).value
                host = host if host else 'localhost'
                port = self.query_one('#port', Input).value
                port = int(port) if port else 1234

                recvSckt.receiver.connect((host, port))
                button.remove_class('connect')
                button.add_class('disconnect')
                event.button.watch_variant('success', 'error')
                event.button.label = 'Disconnect'
                self.controller = ControlRtlTcp(recvSckt.receiver)
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
            except (ConnectionError, OSError) as e:
                recvSckt.receiver = None
                result = str(e)
        elif event.button.has_class('disconnect'):
            recvSckt.receiver = None
            del self.controller
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

    @on(Switch.Changed, '#graph_switch')
    def onGraphChanged(self, event: Switch.Changed) -> None:
        if event.value and self.graphProc is None:
            self.graphSckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.graphSckt.settimeout(1)
            self.graphSckt.connect(self.server.socket.getsockname())
            self.graphProc = Process(target=SpectrumAnalyzer.start,
                                     args=(self.fs, self.graphSckt, self.recvSckt.readSize),
                                     daemon=True)
            self.graphProc.start()
        elif self.graphProc:
            # self.graphSckt.send(b'')
            shutdownSocket(self.graphSckt)
            self.graphSckt.close()
            self.graphProc.join(0.1)
            if self.graphProc.exitcode is None:
                self.graphProc.kill()
            self.graphProc = None
            self.graphSckt = None

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
                            validators=[Function(self.isValidHost, "Please input valid host.")])
                yield Input(placeholder='1234', id='port', classes='source', type='integer', valid_empty=True)
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
        SdrControl.print = log.write
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


if __name__ == '__main__':
    readSize = 65536 if len(sys.argv) < 2 else int(sys.argv[1])
    with SocketReceiver(readSize=readSize) as recvSckt:
        isDead = Value('b', 0)
        isDead.value = 0
        try:
            server, lt, ft = output_server.initServer(recvSckt, isDead)
            ft.start()
            lt.start()

            app = SdrControl(recvSckt, server)
            app.run()
        except KeyboardInterrupt:
            pass
        finally:
            isDead.value = 1
            server.shutdown()
            lt.join(1)
            ft.join(1)
            app.exit(return_code=0)
