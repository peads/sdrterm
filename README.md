# Requirements
* python3 (other requirements will be handled via pip-tools)

#### NOTE
*Supported* Windows functionality is reduced to only using input from files located on a disk because piping binary (i.e. non-text) data between processes in Powershell is only natively supported in Powershell v7.4+ (https://stackoverflow.com/a/68696757/8372013).

Questions/issues regarding this topic are subject to be closed and/or ignored without warning. Just use wsl instead.


# Installing required packages
After cloning this repo perform the following:
```
python -m venv .venv

(if using windows)
.\.venv\Scripts\activate

(otherwise)
.venv/bin/activate

pip install --upgrade pip
pip install pip-tools
pip-compile requirements.in
pip-sync
...
deactivate
```
Plots are optional, but can be activated by uncommenting the line containing `pyqtgraph` in the `requirements.in` file, 
or if it happens to already be installed.
#### NOTE
Default input is expected to be big-endian. To swap this, use the `-X` flag. The single-output setting uses the system-default endianness (e.g. little-endian on the typical x86-based system).
# Examples
## sdrterm.py
#### Plot: Spectrum analyzer
#### Sample rate: 1024k S/s
#### Input data type: 8-bit unsigned-int
#### Input: stdin
#### Output: stdout
`socat -u TCP4:<host>:<port> - | python src/sdrterm.py --fs=1024000 -b8 -eB --plot=ps | ...`

#### Plot: Spectrum analyzer
#### Sample rate: 2400k S/s
#### Input data type: 8-bit unsigned-int
#### Input file.bin
#### Output: stdout -> sox -> dsd
#### Offset from (tuner's) center frequency: -350 kHz
#### Correct IQ: Enabled
#### Decimation factor: 120 times => out fs: 2400k/120 = 20k S/s
#### Output lowpass elliptical filter cutoff frequency: 5 kHz
#### Smooth outliers in output (using Savitzky–Golay filter): Enabled 
#### Pipe the output through `sox` to `dsd`
`src/sdrterm.py --correct-iq -m5000 --plot=ps -c"-3.5E+5" -i file.bin --fs=2400000 -b8 -eB --smooth-output --plot=ps,vfo --decimation 120 | sox -D -traw -r20k -b64 -ef - -traw -es -b16 -r48k - | dsd -i - -o /dev/null -n`

#### Plot: Spectrum analyzer, Multi-VFO Spectrum analyzer
#### Sample rate: Read from RIFF header
#### Input data type: 16-bit signed-int (also, read from RIFF header)
#### Input file.wav
#### Output: sockets listening on all available interfaces (0.0.0.0 specified by the `--vfo-host` option)
##### One socket per offset provided via the `--vfos`  parameter: -60 kHz and 15 kHz in the this example"
##### *NOTE Unlike the normal, single-output setting, the `--simo` setting outputs data as network-default, big-endian doubles*
#### Offset from (tuner's) center frequency: -25 kHz
#### Correct IQ: Enabled
#### Decimation factor: 50 times => out fs: 1024k/50 = 20480 S/s (if you don't know your file's sampling rate, use a tool like `mediainfo`)
#### Output lowpass elliptical filter cutoff frequency: 5 kHz
#### `-X` sepcified since this hypothetical wav file has a standard header (i.e. does not have extended RIFF information) with no endianness information, and its encoding is little-endian
```
src/sdrterm.py -X --correct-iq -m5000 -c"-2.5E+4" -i int16.wav --plot=ps,vfo --decimation 50 --vfos=15000,-60000 --vfo-host=0.0.0.0
...
(In other terminal(s); one for each socket/vfo)

socat TCP4:<host>:<port> - | sox -traw -ef -b64 -r20480 - -traw -es -b16 -r48k - | ...
```

Further options can be found via `python src/sdrterm.py --help` 

N.B. output below may be out of date, the source of truth 
should always be considered version output by the aforementioned option of the code currently committed to  the master branch

```
 Usage: sdrterm.py [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --fs                -r                        INTEGER  Sampling frequency in Samples/s                                                           │
│ --center-frequency  -c                        INTEGER  Offset from tuned frequency in Hz [default: 0]                                            │
│ --input             -i                        TEXT     Input device [default: (stdin)]                                                           │
│ --output            -o                        TEXT     Output device [default: (stdout)]                                                         │
│ --plot                                        TEXT     1D-Comma-separated value of plot type(s) [default: None]                                  │
│ --demod                                       TEXT     Demodulation type [default: fm]                                                           │
│ --tuned-frequency   -t                        INTEGER  Tuned frequency in Hz [default: 0]                                                        │
│ --vfos                                        TEXT     1D-Comma-separated value of offsets from center frequency to process in addition to       │
│                                                        center in Hz                                                                              │
│                                                        [default: None]                                                                           │
│ --decimation                                  INTEGER  Decimation factor [default: 2]                                                            │
│ --encoding          -e                        TEXT     Binary encoding (ignored if wav file) [default: None]                                     │
│ --omega-out         -m                        INTEGER  Output cutoff frequency in Hz [default: 12500]                                            │
│ --correct-iq            --no-correct-iq                Toggle iq correction [default: no-correct-iq]                                             │
│ --simo                  --no-simo                      N.B. unlike normal mode, which uses the system-default endianness for output, the sockets │
│                                                        output  network-default, big-endian bytes. Enable using sockets to output data processed  │
│                                                        from multiple channels specified by the vfos option. [Implies: --vfos <csv>]              │
│                                                        [default: no-simo]                                                                        │
│ --verbose           -v                                 Toggle verbose output                                                                     │
│ --trace                 --no-trace                     Toggle extra verbose output [Implies --verbose] [default: no-trace]                       │
│ --smooth-output         --no-smooth-output             Toggle smoothing output when multi-threading [default: no-smooth-output]                  │
│ --vfo-host                                    TEXT     Address on which to listen for vfo client connections [default: localhost]                │
│ --input-endianness  -X                                 Swap input endianness [default: (False => network-default, big-endian)]                   │
│ --help                                                 Show this message and exit.                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## rtltcp.py
#### rtl_tcp running on server <ip | addr> on \<port>
`python src/rtltcp.py <host> <port>`
```
 Usage: rtltcp.py [OPTIONS] HOST PORT

╭─ Arguments ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    host      TEXT     Address of remote rtl_tcp server [default: None] [required]                                                       │
│ *    port      INTEGER  Port of remote rtl_tcp server [default: None] [required]                                                          │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
<img width="466" alt="Screenshot 2024-06-18 at 20 45 48" src="https://github.com/peads/sdrterm/assets/902685/29812f55-479f-4934-930b-56b2aaf743c4">

## sdrcontrol.py

<img width="993" alt="Screenshot 2024-06-18 at 20 43 23" src="https://github.com/peads/sdrterm/assets/902685/7fd07d90-e79a-47e9-9cec-3ebc7cd446af">
