# Requirements
* python3 (other requirements will be handled via pip)

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

# Example
### sdrterm.py
#### Plot: Spectrum analyzer
#### Sample rate: 1024k S/s
#### Input data type: 8-bit unsigned-int
#### Input: stdin
#### Output: stdout
`socat TCP4:<host>:<port> - | python src/sdrterm.py --fs=1024000 -b8 -eB --plot=ps | ...`
#### Plot: Spectrum analyzer
#### Sample rate: 2400k S/s
#### Input data type: 8-bit unsigned-int
#### Input file.bin
#### Output: stdout -> sox -> dsd
#### Offset from center frequency: -35 kHz
#### Correct IQ: Enabled
#### Decimation factor: 120 times => out fs: 2400k/120 = 20k S/s
#### Output lowpass elliptical filter cutoff frequency: 5 kHz
#### Multi-threaded dsp: Enabled 
#### Smooth outliers in mutli-threaded chunks (using Savitzky–Golay filter): Enabled 
`src/sdrterm.py --correct-iq -m5000 --plot=ps -c"-3.5E+4" -i file.bin --fs=2400000 -b8 -eB --multi-threaded --smooth-output --decimation 120 | sox -D -v0.05 -traw -r20k -b64 -ef - -traw -es -b16 -r48k - | dsd -i - -o /dev/null -n`

Further options can be found via `python src/sdrterm.py --help`
```
 Usage: sdrterm.py [OPTIONS]

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --fs                -r                         INTEGER  Sampling frequency in Samples/s                                           │
│ --center-frequency  -c                         FLOAT    Offset from tuned frequency in Hz [default: 0]                            │
│ --input             -i                         TEXT     Input device [default: (stdin)]                                           │
│ --output            -o                         TEXT     Output device [default: (stdout)]                                         │
│ --plot                                         TEXT     1D-Comma-separated value of plot type(s) [default: None]                  │
│ --demod                                        TEXT     Demodulation type [default: fm]                                           │
│ --tuned-frequency   -t                         INTEGER  Tuned frequency in Hz [default: None]                                     │
│ --vfos                                         TEXT     1D-Comma-separated value of offsets from center frequency to process in   │
│                                                         addition to center in Hz                                                  │
│                                                         [default: None]                                                           │
│ --decimation                                   INTEGER  Decimation factor [default: 2]                                            │
│ --bits-per-sample   -b                         INTEGER  Bits per sample (ignored if wav file) [default: None]                     │
│ --encoding          -e                         TEXT     Binary encoding (ignored if wav file) [default: None]                     │
│ --omega-out         -m                         INTEGER  Cutoff frequency in Hz [default: 12500]                                   │
│ --correct-iq            --no-correct-iq                 Toggle iq correction [default: no-correct-iq]                             │
│ --simo                  --no-simo                       N.B. unlike single-output mode--which uses the system-default endianness  │
│                                                         for output--the sockets output network-default, big-endian bytes. Enable  │
│                                                         using sockets to output data processed from multiple channels specified   │
│                                                         by the vfos option. [Implies: --vfos <csv>]                               │
│                                                         [default: no-simo]                                                        │
│ --verbose           -v                                  Toggle verbose output                                                     │
│ --trace                 --no-trace                      Toggle extra verbose output [default: no-trace]                           │
│ --multi-threaded        --no-multi-threaded             Toggle DSP multithreading [default: no-multi-threaded]                    │
│ --smooth-output         --no-smooth-output              Toggle smoothing output when multi-threading [default: no-smooth-output]  │
│ --vfo-host                                     TEXT     Address on which to listen for vfo client connections                     │
│                                                         [default: localhost]                                                      │
│ --help                                                  Show this message and exit.                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
### rtltcp.py
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

### sdrcontrol.py

<img width="993" alt="Screenshot 2024-06-18 at 20 43 23" src="https://github.com/peads/sdrterm/assets/902685/7fd07d90-e79a-47e9-9cec-3ebc7cd446af">
