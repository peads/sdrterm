# Installation
`pip install sdrterm`

*NOTE: Unless you intend use code on the bleeding-edge, or to modify the source, skip ahead to [here](#notes).
# Requirements
After cloning this repo perform the following:
```
cd <path/to/clone>
python -m venv .venv

(if using windows)
.\.venv\Scripts\activate

(otherwise)
source .venv/bin/activate

(either)
pip install .
(or to include optional graphing dependencies)
pip install .[gui]

...<do stuff here>...

deactivate
```
Alternatively--if you do not wish to use a virtual environment--the dependencies may be installed via the system's 
package manager; or, with caution, using `pip` directly.

*Plotting support is optional, and dependencies can be installed by specifying by the 
`[gui]` option during install, or if they happen to already be installed in the environment.*
## Notes
### Input data
* For raw files, input is system-default endianness, 
* For wave files, the endianness defined by the RIFF/X header
* For tcp connections, data is expected to be big-endian
* Endianness can be inverted using the `-X` flag
* When necessary to specify the input datatype (`-e` flag), the selections map exactly to the "integer" and "float" types listed [here](https://docs.python.org/3/library/struct.html#format-characters)
### Ouput data
* Standard mode outputs doubles (float64) with system-default endianness and alignment
* Multiple VFO mode (`--simo` flag) output is always big-endian doubles
### Misc
* Be aware that piping binary (i.e. non-text) data between processes in Powershell is only natively-supported 
in Powershell v7.4+ (https://stackoverflow.com/a/68696757/8372013), which you may have 
to install separately from the default version included with your copy of Windows. 
*N.B. this does not affect modes that use sockets for IO.*
# Examples
## sdrterm.py
### Read input from wave file
`python -m sdrterm -i file.wav --omega-out=5k --decimation=64 --center-frequency="15k" --plot=spec --correct-iq -o out.bin`
#### General explanation of options
* Input source: wave file
* Input data type: determined by RIFF/X header metadata
* Sample rate: determined by RIFF/X header metadata ($fs$ $S \over s$)
* Output lp: 5 kHz
* Decimation factor: $64 \implies$ $fs \over 64$ $S \over s$
* Offset from tuned frequency: +15 kHz
* Plot(s): Spectrum Analyzer
* IQ correction: enabled
* Output destination: out.bin
### Read input from socket, and pipe output to stdout 
`python -m sdrterm -i <host>:<port> -eh -r1024k -w5k -d64 -c"-30k" --plot=water | ...`
#### General explanation of options
*N.B. sampling rate and datatype must be specified for raw input*
* Input source: TCP socket at \<host> on \<port>
* Input data type: 16-bit, signed integer
* Sample rate: $1024k$ $S \over s$
* Output lp: 5 kHz
* Decimation factor: $64 \implies$ $1024k \over 64$ $= 16k$ $S \over s$
* Offset from tuned frequency: -30 kHz
* Plot(s): Waterfall
* Output destination: stdout
### Select multiple frequencies to process from data input via a socket and output them via separate sockets
#### See [exmaple_simo.sh](example_simo.sh) for a complete example

*More examples can be found in the shell scripts  in the root of this repo.* 
```
 Usage: sdrterm.py [OPTIONS]

╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --fs                     -r                          NUMBER                 Sampling frequency in k/M/Samples per sec                                                                                                 │
│ --center-frequency       -c                          NUMBER                 Offset from tuned frequency in k/M/Hz [default: 0]                                                                                        │
│ --input                  -i                          TEXT                   Input device [default: (stdin)]                                                                                                           │
│ --output                 -o                          TEXT                   Output device [default: (stdout)]                                                                                                         │
│ --plot                                               TEXT                   1D-Comma-separated value of plot type(s) [default: None]                                                                                  │
│ --demodulation           -m                          [fm|wfm|am|re|im|fft]  Demodulation type [default: fm]                                                                                                           │
│ --tuned-frequency        -t                          NUMBER                 Tuned frequency in k/M/Hz [default: 0]                                                                                                    │
│ --vfos                                               TEXT                   1D-Comma-separated value of offsets from tuned frequency to process in addition to tuned frequency in k/M/Hz [default: None]              │
│ --decimation             -d                          INTEGER RANGE [x>=2]   Decimation factor [default: 2]                                                                                                            │
│ --encoding               -e                          [b|B|h|H|i|I|f|d]      Binary encoding (ignored if wav file) [default: None]                                                                                     │
│ --omega-out              -w                          NUMBER                 Output cutoff frequency in k/M/Hz [default: 12500]                                                                                        │
│ --correct-iq                 --no-correct-iq                                Toggle iq correction [default: no-correct-iq]                                                                                             │
│ --simo                       --no-simo                                      Enable using sockets to output data processed from multiple channels specified by the vfos option. N.B. unlike normal mode, which uses    │
│                                                                             the system-default endianness for output, the sockets output  network-default, big-endian doubles. [Implies: --vfos <csv>]                │
│                                                                             [default: no-simo]                                                                                                                        │
│ --verbose                -v                          INTEGER                Toggle verbose output. Repetition increases verbosity (e.g. -vv, or -v -v) [default: 0]                                                   │
│ --smooth-output                                      INTEGER                Provide length of polynomial for smoothing output with Savitzky–Golay filter. A larger polynomial implies more aggressive filtering.      │
│                                                                             [default: (0 => no filtering)]                                                                                                            │
│ --vfo-host                                           TEXT                   Address on which to listen for vfo client connections [default: localhost]                                                                │
│ --swap-input-endianness  -X                                                 Swap input endianness [default: (False => system-default, or as defined in RIFF header)]                                                  │
│ --normalize-input            --no-normalize-input                           Normalize input data. [default: no-normalize-input]                                                                                       │
│ --help                                                                      Show this message and exit.                                                                                                               │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## rtltcp.py
#### rtl_tcp running on server <ip | addr> on \<port>
`python -m rtltcp <host> <port>`
```
 Usage: rtltcp.py [OPTIONS] HOST PORT

╭─ Arguments ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    host      TEXT     Address of remote rtl_tcp server [default: None] [required]                                                                                                                                   │
│ *    port      INTEGER  Port of remote rtl_tcp server [default: None] [required]                                                                                                                                      │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --server-host        TEXT  Port of local distribution server [default: localhost]                                                                                                                                     │
│ --help                     Show this message and exit.                                                                                                                                                                │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
<img width="466" alt="Screenshot 2024-06-18 at 20 45 48" src="https://github.com/peads/sdrterm/assets/902685/29812f55-479f-4934-930b-56b2aaf743c4">

## sdrcontrol.py [EXPERIMENTAL]

<img width="993" alt="Screenshot 2024-06-18 at 20 43 23" src="https://github.com/peads/sdrterm/assets/902685/7fd07d90-e79a-47e9-9cec-3ebc7cd446af">

*Due to the experimental nature of this interface, do not hesitate to report suspected bugs.*

*N.B. if you'd like to be sure of your wave file's sampling rate beforehand, 
you can use a tool like `mediainfo` available via most POSIX-like systems' package managers. 
Also, basic information about the input file, and other settings are output in JSON format at beginning
of sdrterm's operation. e.g.,*
```
{
  "bandwidth": 12500,
  "centerFreq": 0,
  "tunedFreq": 0,
  "omegaOut": 5000,
  "fs": 48000,
  "decimatedFs": 24000
}
```
