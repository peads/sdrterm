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
from contextlib import closing
from multiprocessing import Value, Process

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Center, Container
from textual.reactive import reactive
from textual.validation import Function
from textual.widgets import Button, RichLog, Input, Select, Label, Switch
from textual_slider import Slider

from misc.general_util import shutdownSocket, shutdownSockets
from plots.spectrum_analyzer import SpectrumAnalyzer
from sdr.control_rtl_tcp import ControlRtlTcp
from sdr.output_server import OutputServer
from sdr.rtl_tcp_commands import RtlTcpSamplingRate, RtlTcpCommands
from sdr.socket_receiver import SocketReceiver


class SdrControl(App):
    CSS = '''    
        Vertical {
            padding: 0;
            margin: 0;
        }
        Horizontal {
            padding: 0;
            margin: 0;
        }
        Label {
            padding: 0;
            margin: 0;
        }
        Container {
            padding: 0;
            margin: 0;
        }
        Input#host {
            width: 66%;
        }
        Input#port {
            width: 15%;
        }
        Input#frequency {
            width: 75%;
        }
        Button#connector {
            width: 19%;
        }
        Button#set_freq {
            width: 25%;
        }
    '''
    offset = reactive(0)
    fs = reactive(0)

    def __init__(self, rs: socket, ls: socket, srv: OutputServer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graphSckts = None
        self.recvSckt = rs
        self.listenerSckt = ls
        self.controller = None
        self.server = srv
        self.graphProc = None

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
                freq = int(freq) if freq else 100000000
                agc = self.query_one('#agc_switch', Switch).value
                agc = agc if agc else 0
                dagc = self.query_one('#dagc_switch', Switch).value
                dagc = dagc if dagc else 0

                self.controller.setFs(fs)
                self.controller.setFrequency(freq + self.offset)
                self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE.value, 1 - agc)
                self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, dagc)
                self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, gain)

                gainsSlider.value = gain
                fsList.value = fs
                frequency.value = str(freq)

                result = f'Accepting connections on port {self.server.port}'
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
        self.query_one(RichLog).write(result)

    @on(Select.Changed, '#fs_list')
    def onFsChanged(self, event: Select.Changed) -> None:
        self.fs = event.value if str(event.value) != "Select.BLANK" else 0
        if self.controller:
            self.controller.setFs(self.fs)

    @on(Button.Pressed, '#set_freq')
    def onFreqPressed(self, _: Button.Pressed) -> None:
        if self.controller:
            value = self.query_one('#frequency', Input).value
            value = int(value) if value else 0
            self.controller.setFrequency(value + self.offset)

    @on(Input.Changed, '#offset')
    def onOffsetChanged(self, event: Input.Changed) -> None:
        value = event.value
        self.offset = int(value) if value and value != '-' else 0

    @on(Slider.Changed, '#gains_slider')
    def onGainsChanged(self, event: Slider.Changed) -> None:
        value = event.value
        label = self.query_one('#gains_label', Label)
        label.update(str(value))
        if self.controller:
            self.controller.setParam(RtlTcpCommands.SET_TUNER_GAIN_BY_INDEX.value, value)

    @on(Switch.Changed, '#agc_switch')
    def onAgcChanged(self, event: Switch.Changed) -> None:
        if self.controller:
            value = event.value
            self.controller.setParam(RtlTcpCommands.SET_GAIN_MODE.value, 1 - value)

    @on(Switch.Changed, '#dagc_switch')
    def onDagcChanged(self, event: Switch.Changed) -> None:
        if self.controller:
            value = event.value
            self.controller.setParam(RtlTcpCommands.SET_AGC_MODE.value, value)

    @on(Switch.Changed, '#graph_switch')
    async def onGraphChanged(self, event: Switch.Changed) -> None:
        if event.value and self.graphProc is None:
            w, r = self.graphSckts = socket.socketpair()
            self.graphProc = Process(target=SpectrumAnalyzer.start,
                                     args=(self.fs, r, self.recvSckt.writeSize),
                                     daemon=True)
            self.graphProc.start()
            self.server.clients.put(w)
        elif self.graphProc:
            w, r = self.graphSckts
            w.send(b'')
            shutdownSockets(self.graphSckts)
            [x.close() for x in self.graphSckts]
            self.graphProc.join(0.1)
            if self.graphProc.exitcode is None:
                self.graphProc.kill()
            self.graphProc = None
            self.graphSckts = None

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label('Source')
            yield Horizontal(
                Input(placeholder='localhost', id='host', classes='source', valid_empty=True,
                      validators=[Function(self.isValidHost, "Please input valid host.")]),
                Input(placeholder='1234', id='port', classes='source', type='integer', valid_empty=True),
                Button('Connect', id='connector', classes='connect', variant='success')
            )
            yield Label('Tuning')
            yield Horizontal(
                Input(placeholder='100000000 Hz', id='frequency', classes='frequency', type='integer'),
                Button('Set', id='set_freq', classes='frequency')
            )
            yield Label('Offset')
            yield Container(Input(placeholder='35000 Hz', id='offset', classes='offset', type='integer'))
            yield Label('Sampling Rate')
            yield Select(RtlTcpSamplingRate.tuples(), prompt='Rate', classes='fs', id='fs_list')
            yield Vertical(
                Center(Label('Spectrum Equalizer')),
                Center(Switch(id='graph_switch'))
            )
            yield Label('Gains')
            yield Horizontal(
                Vertical(
                    Center(Label('Gain', id='gains_label')),
                    Center(Slider(0, 28, id='gains_slider'))
                ),
                Vertical(
                    Center(Label('LNA')),
                    Center(Switch(id='agc_switch'))
                ),
                Vertical(
                    Center(Label('VGA')),
                    Center(Switch(id='dagc_switch'))
                )
            )

        yield RichLog(highlight=True)

    def on_mount(self) -> None:
        label = self.query_one('#gains_label', Label)
        label.update(str(self.query_one('#gains_slider', Slider).value))

    @staticmethod
    def isValidHost(value: str) -> bool:
        length = len(value) if value else 0
        if length < 1:
            return True

        if length and '-' in value[0]:
            return False

        value = value[-1]
        if (value.isalpha()
                or value.isnumeric()
                or '-' in value
                or '.' in value):
            return True

        return False


if __name__ == '__main__':
    with SocketReceiver() as recvSckt:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as listenerSckt:
            isDead = Value('b', 0)
            isDead.value = 0
            with OutputServer(isDead, host='0.0.0.0') as server:
                try:
                    lt, ft = server.initServer(recvSckt, listenerSckt, isDead)
                    ft.start()
                    lt.start()

                    app = SdrControl(recvSckt, listenerSckt, server)
                    app.run()
                except KeyboardInterrupt:
                    pass
                finally:
                    shutdownSocket(listenerSckt)
                    isDead.value = 1
                    lt.join(1)
                    ft.join(1)
                    app.exit(return_code=0)
