# Requirements
python3
#### NOTE
Windows functionality is reduced to only using input from files located on a disk because piping binary (i.e. non-text) data between processes in Powershell is only natively supported in Powershell v7.4+ (https://stackoverflow.com/a/68696757/8372013).

Questions/issues regarding this topic are subject to be close and ignored without warning.


# Installing required packages
After cloning this repo perform the following:
```
python -m venv .venv

(if using windows)
.\.wenv\Scripts\activate
(otherwise)
.venve/bin/activate

python setup.py egg_info
pip install -r src/sdrterm.egg-info
...
deactivate
```
Alternatively, 
