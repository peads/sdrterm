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
host="localhost:1234";
port=0;
outPath="/mnt/d";
decimation=64;
offset="-3.5E+5";
fs=1024000;
vfos="15000,-60000,525000";
logFiles=();
tuned=0;

if [[ ! -z "$2" ]]; then
  fs="$2";
fi

if [[ ! -z "$3" ]]; then
  decimation="$3";
fi

if [[ ! -z "$4" ]]; then
  offset="$4";
fi

if [[ ! -z "$5" ]]; then
  tuned="$5";
fi

if [[ ! -z "$6" ]]; then
  vfos="$6"
fi

cmd="socat TCP4:${1} -";
set -u;
echo "LOG: ${cmd}";
coproc SOCAT { eval "$cmd"; }
exec {SOCAT_IN}<&${SOCAT[0]}- {SOCAT_OUT}>&${SOCAT[1]}-
unset cmd;

cmd="python src/sdrterm.py ${7} -c${offset} -t${tuned} --vfos=${vfos} --correct-iq -r${fs} -eB --simo --decimation=${decimation} -w5000 2>&1 0<&${SOCAT_IN}";
set -u;
echo "LOG: ${cmd}";
coproc SDRTERM { eval "$cmd"; }
exec {SDR_IN}<&${SDRTERM[0]}- {SDR_OUT}>&${SDRTERM[1]}-
unset cmd;

port="";
decimatedFs="";
while IFS= ; read -r line; do
  echo "LOG: ${line}"
  if [[ ! -z $(echo $line | grep "vfos" -) ]]; then
    vfos=$(sed -E "s/^\s*\"vfos\":\s+\"((-*[0-9]+,*)+)\",*\s*$/\1/g" <<< $line);
  fi
  if [[ ! -z $(echo $line | grep "tunedFreq" -) ]]; then
    tuned=$(sed -E "s/^\s*\"tunedFreq\":\s+([0-9]+),*\s*$/\1/g" <<< $line);
  fi
  if [[ ! -z "$(echo $line | grep "decimatedFs" -)" ]]; then
    decimatedFs=$(echo $line | sed -E "s/^\s*\"decimatedFs\":\s+([0-9]+),*\s*$/\1/g");
  fi
  if [[ $line == *"Accepting"* ]]; then
    port=$(echo $line | grep "Accepting" - | sed -E "s/^.*\('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', ([0-9]+)\).*$/\1/g");
    break;
  fi
done <&"${SDR_IN}"

declare -A pipes;
declare -A pids;
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
  cmd="socat TCP4:localhost:${port} - | sox -q -D -B -traw -b64 -ef -r${decimatedFs} - -traw -b16 -es -r48k - 2>/dev/null | dsd -i - -o /dev/null -n -f1 -w ${outPath}/out-${freq}.wav 2>&1;" #> ${fileName};"
  set -u;

  logFiles=("${logFiles[@]}" "$fileName");

  echo "LOG: ${cmd}";
  eval "coproc ${coprocName} { ${cmd} }"
  eval "exec {tmp_in}<&\${${coprocName}[0]}- {tmp_out}>&\${${coprocName}[1]}-";
  eval "pids[\"${coprocName}\"]=\${${coprocName}_PID}";
  eval "pipes[\"${coprocName}\",1]=${tmp_in}; pipes[\"${coprocName}\",2]=${tmp_out}";

  unset fileName;
  unset coprocName;
  unset freq;
  unset cmd;
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
bar="\0"
for i in "${!pids[@]}"; do
  echo "LOG: Awaiting ${i}";
  eval "wait ${pids[$i]}";
  while IFS= ; read -r line; do
    IFS=_ ; read -ra splt <<< "$i";
    freq=${splt[1]};
    freq=$(( freq / 1000 ));
    echo "LOG_${freq}: ${line}";
  done <&"${pipes[${i},1]}"
done
unset i;
