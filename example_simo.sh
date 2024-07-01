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
OIFS=$IFS
echo "LOG: $OIFS"
END=10;
set -u;
port=0;
outPath="/mnt/d";
params=""
i="\0";

set -u
for i in ${@:2}; do
    params+="${i} ";
done
unset i;

cmd="socat TCP4:${1} -";
set -u;
echo "LOG: ${cmd}";
coproc SOCAT { eval "$cmd"; }
exec {SOCAT_IN}<&${SOCAT[0]}- {SOCAT_OUT}>&${SOCAT[1]}-
unset cmd;

cmd="python src/sdrterm.py ${params} --simo 2>&1 0<&${SOCAT_IN}";
set -u;
echo "LOG: ${cmd}";
coproc SDRTERM { eval "$cmd"; }
exec {SDR_IN}<&${SDRTERM[0]}- {SDR_OUT}>&${SDRTERM[1]}-
unset cmd;

host="";
port="";
decimatedFs="";

function generateRegex {
  echo "s/^\s*\"${1}\":\s*${2},*\s*$/\1/g"
}

while IFS= ; read -r line; do
  echo "LOG: ${line}"
  if [[ ! -z $(echo $line | grep "host" -) ]]; then
    host=$(sed -E "`generateRegex "host" '\"(([a-zA-Z0-9]+)+)\"'`" <<< $line);
  fi
  if [[ ! -z $(echo $line | grep "vfos" -) ]]; then
    vfos=$(sed -E "`generateRegex "vfos" '\"((-*[0-9]+,*)+)\"'`" <<< $line);
  fi
  if [[ ! -z $(echo $line | grep "tunedFreq" -) ]]; then
    tuned=$(sed -E "`generateRegex "tunedFreq" "([0-9]+)"`" <<< $line);
  fi
  if [[ ! -z "$(echo $line | grep "decimatedFs" -)" ]]; then
    decimatedFs=$(sed -E "`generateRegex "decimatedFs" "([0-9]+)"`" <<< $line);
  fi
  if [[ $line == *"Accepting"* ]]; then
    port=$(echo $line | grep "Accepting" - | sed -E "s/^.*\('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+',\s*([0-9]+)\).*$/\1/g");
    break;
  fi
done <&"${SDR_IN}"

declare -A pipes;
declare -A pids;
declare -A logFiles;

i="\0";
set -u;
IFS=, ; read -r -a vfos <<< "$vfos";
for i in "${vfos[@]}"; do
  tmp_in="\0";
  set -u;
  tmp_out="\0";
  set -u;
  freq=$(( i + tuned ));
  set -u;
  coprocName="SOCAT_${freq}";
  set -u;
  fileName="/tmp/log-${freq}";
  set -u;
  cmd="socat TCP4:${host}:${port} - | sox -q -D -B -traw -b64 -ef -r${decimatedFs} - -traw -b16 -es -r48k - 2>/dev/null | dsd -i - -o /dev/null -n -f1 -w ${outPath}/out-${freq}.wav 2>&1 > ${fileName}"
  set -u;

  echo "LOG: ${cmd}";
  eval "coproc ${coprocName} { ${cmd}; }"
  eval "exec {tmp_in}<&\${${coprocName}[0]}- {tmp_out}>&\${${coprocName}[1]}-";
  eval "pids[\"${coprocName}\"]=\${${coprocName}_PID}";
  eval "pipes[\"${coprocName}\",1]=${tmp_in}; pipes[\"${coprocName}\",2]=${tmp_out}";
  logFiles["${coprocName}"]=${fileName};

  unset fileName;
  unset cmd;
  unset freq;
  unset coprocName;
  unset tmp_in;
  unset tmp_out;
done
unset i;

echo "LOG: ${pids[@]}";
echo "LOG: ${pipes[@]}";
echo "LOG: ${logFiles[@]}";

while IFS= ; read -r line; do
  echo "LOG: ${line}"
  if [[ $line == *"established"* ]]; then
    break;
  fi
done <&"${SDR_IN}"

echo "LOG: Awaiting sdrterm"
wait $SDRTERM_PID;

i="\0";
set -u;
for i in "${!pids[@]}"; do
  echo "LOG: Awaiting ${i}";
  wait ${pids["$i"]};
  while IFS= ; read -r line; do
    echo "LOG: ${line}";
  done < ${logFiles["$i"]}
done
unset i;