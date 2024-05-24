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
#### Input data type: 8-bit unsigned-int
#### Input: stdin
#### Output: stdout
`nc <host> <port> | python src/sdrterm.py --fs=1024000 -b8 -eB --plot=ps | ...`

Further options can be found via `python src/sdrterm.py --help`
### rtltcp.py
#### rtl_tcp running on server <ip | addr> on \<port>
`python src/rtltcp.py <host> <port>`

Options are explained upon successful connection
