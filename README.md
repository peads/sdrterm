# Requirements
## Installing required dependencies
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
package manager; or, with caution, `pip` directly.

*Plotting support is optional, and can be activated by uncommenting the line containing `pyqtgraph` and adding a Qt framework in the `requirements.in` file
before running `pip-compile`, or if it happens to already be installed in the environment.*
### NOTE
* By default, raw input is expected to be big-endian. 
  * To swap this, use the `-X` flag. 
* The endianness of the wave files is determined from metadata.
* The default output mode (i.e. to stdin, or a file) double (float64) of the system-default endianness and alignment.
  * e.g., doubles are 8 or 4 byte-aligned, little-endian on the typical x86-based system using Windows and Linux respectively.
* By default, simo mode outputs big-endian doubles to its sockets.
# Examples
## sdrterm.py
### Pipe output processed from wave file through `sox` then `dsd`
`src/sdrterm.py -X --correct-iq -w5k --plot=ps -c"-3.5E+5" -i file.wav --plot=ps --decimation 100 | sox -D -traw -r24k -b64 -ef - -traw -es -b16 -r48k - | dsd -i - -o /dev/null -n`
#### Explanation of options
*N.B. the `-X` flag is specified since this hypothetical wav file has only standard header 
information (i.e. does not have extended RIFF data) with no endianness indicator, 
and its encoding is little-endian*

Plot(s): Spectrum analyzer

Endianness swap: Enabled

Sample rate: Determined via RIFF header

Input data type: Determined via RIFF header

Input source: file.wav

Output destination(s): stdout -> sox -> dsd

Offset from (tuner's) center frequency: -350 kHz

IQ correction: Enabled

Decimation factor: 100 times => output fs: 2400k/100 = 24k S/s 

Output lowpass elliptical filter cutoff frequency: 5 kHz

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
  "smooth": 0,
  "fs": 48000,
  "decimatedFs": 24000
}
```
### Pipe raw data from `socat` in, and output to pipe via stdout 
*N.B. sampling rate and datatype must be specified for raw input*

`socat -u TCP4:<host>:<port> - | python src/sdrterm.py -w18k --fs=1024k -t162.5M -c"-30k" -eh --plot=water | ...`
#### Explanation of options
Plot(s): Waterfall

Sample rate: 1024k S/s

Tuned frequency (only used to make frequency axis of plots clearer): 162.500Mhz

Offset from tuned frequency: -30 kHz

Input data type: 16-bit, signed integer

Input source: socat->stdin

Output destination(s): stdout

Decimation factor: default (i.e. 2 => output fs is 1024k/2 = 512k S/s)

Output lp: 18 kHz

### Select multiple frequencies to process from data piped via `socat` and output them via separate sockets
*See [exmaple_simo.sh](example_simo.sh) for a complete example*
#### General explanation of options
Input source: piped via stdin from `socat`

Output destination(s): server listening for connections on all available interfaces (i.e. on "0.0.0.0" specified by the `--vfo-host` 
option) distributing respective data on sockets; one for each channel frequency specified 

*N.B. Unlike the normal, single-output mode, the `--simo` setting outputs data as network-default, big-endian doubles 
to its socket(s)*

Offset from tuned frequency: +15 kHz

IQ correction: Enabled

Decimation factor: 50 => output fs: 1024k/50 = 20480 S/s

Output lp: 18 kHz

*Less trivial examples can be found in the shell scripts of the form `example*.sh` in the root of this repo.*

#### Further options can be found via `python src/sdrterm.py --help` 

*N.B. output below may be out of date, the source of truth 
should always be considered version output by the aforementioned option 
in the code currently committed to the master branch*

```
 Usage: sdrterm.py [OPTIONS]

╭─ Options ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --fs                     -r                     NUMBER                 Sampling frequency in k/M/Samples per sec                                                                                       │
│ --center-frequency       -c                     NUMBER                 Offset from tuned frequency in k/M/Hz [default: 0]                                                                              │
│ --input                  -i                     TEXT                   Input device [default: (stdin)]                                                                                                 │
│ --output                 -o                     TEXT                   Output device [default: (stdout)]                                                                                               │
│ --plot                                          TEXT                   1D-Comma-separated value of plot type(s) [default: None]                                                                        │
│ --demodulation           -m                     [fm|wfm|am|re|im|fft]  Demodulation type [default: fm]                                                                                                 │
│ --tuned-frequency        -t                     NUMBER                 Tuned frequency in k/M/Hz [default: 0]                                                                                          │
│ --vfos                                          TEXT                   1D-Comma-separated value of offsets from tuned frequency to process in addition to tuned frequency in k/M/Hz [default: None]    │
│ --decimation             -d                     INTEGER RANGE [x>=2]   Decimation factor [default: 2]                                                                                                  │
│ --encoding               -e                     [b|B|h|H|i|I|f|d]      Binary encoding (ignored if wav file) [default: None]                                                                           │
│ --omega-out              -w                     NUMBER                 Output cutoff frequency in k/M/Hz [default: 12500]                                                                              │
│ --correct-iq                 --no-correct-iq                           Toggle iq correction [default: no-correct-iq]                                                                                   │
│ --simo                       --no-simo                                 N.B. unlike normal mode, which uses the system-default endianness for output, the sockets output  network-default, big-endian   │
│                                                                        bytes. Enable using sockets to output data processed from multiple channels specified by the vfos option. [Implies: --vfos      │
│                                                                        <csv>]                                                                                                                          │
│                                                                        [default: no-simo]                                                                                                              │
│ --verbose                -v                     INTEGER                Toggle verbose output. Repetition increases verbosity (e.g. -vv, or -v -v) [default: 0]                                         │
│ --smooth-output                                 INTEGER                Provide length of polynomial for smoothing output with Savitzky–Golay filter. A larger polynomial implies more aggressive       │
│                                                                        filtering.                                                                                                                      │
│                                                                        [default: (0 => no filtering)]                                                                                                  │
│ --vfo-host                                      TEXT                   Address on which to listen for vfo client connections [default: localhost]                                                      │
│ --swap-input-endianness  -X                                            Swap input endianness [default: (False => network-default, big-endian)]                                                         │
│ --help                                                                 Show this message and exit.                                                                                                     │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
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

## sdrcontrol.py [EXPERIMENTAL]

<img width="993" alt="Screenshot 2024-06-18 at 20 43 23" src="https://github.com/peads/sdrterm/assets/902685/7fd07d90-e79a-47e9-9cec-3ebc7cd446af">

*Due to the experimental nature of this interface, do not hesitate to report suspected bugs.*

## Notes
* Default input is expected to be big-endian, but this can be swapped with the `-X` flag
  * When necessary to specify the input *datatype*, the selections map exactly to [the "integer" and "float" types listed here](https://docs.python.org/3/library/struct.html#format-characters)
* Default output mode always uses the system's default-endianness and alignment for the double (float64) datatype
* Multiple VFO mode (i.e. when using the `--simo` flag) output is always big-endian double
* Be aware that piping binary (i.e. non-text) data between processes in Powershell is only natively-supported 
in Powershell v7.4+ (https://stackoverflow.com/a/68696757/8372013), which you may have 
to install separately from the default version included with your copy of Windows, if you wish to 
handle data via that method. *N.B. this does not affect modes that directly use sockets for IO.*
