#!/bin/bash
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
####
# Usage: ./example.sh <wave_file>
####
OUT_PATH=/mnt/d/testing/

function runStdinTest {
  time sox -q -D -twav ${1} -traw -b${3} -e${4} -B - 2>/dev/null \
    | python src/sdrterm.py -w5000 -e${5} -r48000 ${2} 2>/dev/null \
    | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
    | dsd -q -i - -o /dev/null -n -w ${OUT_PATH}/out${5}.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
}

function runFileInTest {
time python src/sdrterm.py -i ${2} -w5000 2>/dev/null \
  | sox -q -D -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${OUT_PATH}/out${1}.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
  rm -f /tmp/tmp.wav;
}

echo "START basic raw stdin test";
runStdinTest "$1" "$2" "16" "s" "h"
printf "END basic raw stdin test\n\n";

runStdinTest "$1" "--normalize-input ${2} " "8" "unsigned-int" "B"
runStdinTest "$1" "--normalize-input ${2} " "32" "s" "i"
runStdinTest "$1" "--normalize-input ${2} " "32" "f" "f"
runStdinTest "$1" "--normalize-input ${2} " "64" "f" "d"

echo "START basic wave file test";
runFileInTest "i16" "$1"
printf "END basic wave file test\n\n";
