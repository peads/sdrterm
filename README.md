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
.\.wenv\Scripts\activate
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
#### Sample rate: 1024k
#### Data type: 8-bit unsigned-int
#### Input: stdin
#### Output: stdout
#### Plots: ps - power spectrum
`nc <host> <port> | python src/sdrterm.py --fs=1024000 -b8 -eB --plot=ps | ...`
#### Input file.wav
#### Output: /dev/null
#### Plots: ps - power spectrum, water - waterfall
`python src/sdrterm.py -i file.wav --plot=ps,water -o /dev/null`

Further options can be found via `python src/sdrterm.py --help`
```
 Usage: sdrterm.py [OPTIONS]

╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --sampling-rate,--fs                         INTEGER  Sampling frequency in Samples/s                                │
│ --center-frequency    -c                     FLOAT    Offset from tuned frequency in Hz [default: 0]                 │
│ --input               -i                     TEXT     Input device [default: (stdin)]                                │
│ --output              -o                     TEXT     Output device [default: (stdout)]                              │
│ --plot                                       TEXT     1D-Comma-separated value of plot type(s) [default: None]       │
│ --demod                                      TEXT     Demodulation type [default: fm]                                │
│ --tuned-frequency     -t                     INTEGER  Tuned frequency in Hz [default: None]                          │
│ --vfos                                       TEXT     1D-Comma-separated value of offsets from center frequency to   │
│                                                       process in addition to center in Hz                            │
│                                                       [default: None]                                                │
│ --decimation                                 INTEGER  Decimation factor [default: 2]                                 │
│ --bits-per-sample     -b                     INTEGER  Bits per sample (ignored if wav file) [default: None]          │
│ --encoding            -e                     TEXT     Binary encoding (ignored if wav file) [default: None]          │
│ --normalize               --no-normalize              Toggle normalizing input analytic signal                       │
│                                                       [default: no-normalize]                                        │
│ --omega-out           -m                     INTEGER  Cutoff frequency in Hz [default: 12500]                        │
│ --correct-iq              --no-correct-iq             Toggle iq correction [default: no-correct-iq]                  │
│ --simo                    --no-simo                   EXPERIMENTAL enable using sockets to output data processed     │
│                                                       from multiple channels specified by the vfos option            │
│                                                       [default: no-simo]                                             │
│ --verbose             -v                              Toggle verbose output                                          │
│ --trace                   --no-trace                  Toggle extra verbose output [default: no-trace]                │
│ --read-size                                  INTEGER  Size in bytes read per iteration [default: 65536]              │
│ --help                                                Show this message and exit.                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
### rtltcp.py
#### rtl_tcp running on server <ip | addr> on \<port>
`python src/rtltcp.py <host> <port>`

Options are explained upon successful connection