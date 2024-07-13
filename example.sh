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
if [[ -z ${SDRTERM_EXEC} ]]; then
  SDRTERM_EXEC="python -m sdrterm";
fi

if [[ -z ${DSD_CMD} ]]; then
  DSD_CMD="dsd -q -i - -o /dev/null -n";
fi

if [[ -z ${OUT_PATH} ]]; then
  OUT_PATH=/mnt/d/simo;
fi

function runStdinTest {
  fileName="${OUT_PATH}/out${4}${6}.wav";
  echo "$fileName";
  time sox -q -D -twav ${1} -traw -b${2} -e${3} ${6} - 2>/dev/null \
    | ${SDRTERM_EXEC} -w5000 -e${4} -r48000 ${5} 2>/dev/null \
    | sox -q -D -v0.5 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
    | ${DSD_CMD} -w "$fileName" 2>&1 | grep "Total" - | grep -E --color=always '[0-9]+' -;
}

function runFileInTest {
  time ${SDRTERM_EXEC} -i ${1} -w5k ${3} 2>/dev/null \
    | sox -q -v0.8 -D -traw -ef -b64 -r24k - -traw -es -b16 -r48k - 2>/dev/null \
    | ${DSD_CMD} -w "${OUT_PATH}/out${2}.wav" 2>&1 | grep "Total" - | grep -E --color=always '[0-9]+' -;
  rm -f /tmp/tmp.wav;
}

echo "START basic raw stdin test";
runStdinTest "$1" "16" "s" "h"
runStdinTest "$1" "8" "unsigned-int" "B" "--correct-iq"
runStdinTest "$1" "32" "s" "i"
runStdinTest "$1" "32" "f" "f"
runStdinTest "$1" "64" "f" "d"

runStdinTest "$1" "16" "s" "h" "-X" "-B"
runStdinTest "$1" "32" "s" "i" "-X" "-B"
runStdinTest "$1" "32" "f" "f" "-X" "-B"
runStdinTest "$1" "64" "f" "d" "-X" "-B"
printf "END basic raw stdin test\n\n";

echo "START basic wave file test";
runFileInTest "$1" "i16"

sox -q -D -twav ${1} -twav -eunsigned-int -r48k -b8 /tmp/tmp.wav 2>/dev/null;
runFileInTest "/tmp/tmp.wav" "u8" "--correct-iq"
