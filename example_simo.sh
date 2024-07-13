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
# Usage: ./example_simo.sh -i [<file> | <host>:<port>] -eB -r1024k -d25 -c"-1.2E+3" -t123.456M" --vfos=15000,-15000,30000" -w5k
####
OIFS=$IFS

function log {
  echo "$(date +'%F %T')Z: ${1}";
}

ts=$(date +%Y%m%d%H%M);
log "timestamp: ${ts}";

if [[ -z ${SDRTERM_EXEC} ]]; then
  SDRTERM_EXEC="python -m sdrterm";
fi

if [[ -z ${DSD_CMD} ]]; then
  DSD_CMD="dsd -q -i - -o /dev/null -n";
fi

if [[ -z ${OUT_PATH} ]]; then
  OUT_PATH=/mnt/d/simo;
fi

declare -A pids;
port=0;
params=""
i="\0";
set -u
for i in ${@:1}; do
  params+="${i} ";
done
unset i;

cmd="${SDRTERM_EXEC} ${params} --simo 2>&1";
set -u;
echo "LOG: ${cmd}";
coproc SDRTERM { eval "$cmd"; }
exec {SDR_IN}<&${SDRTERM[0]}- {SDR_OUT}>&${SDRTERM[1]}-
unset cmd;
pids[0]="${SDRTERM_PID}";

host="";
port="";
decimatedFs="";
mainPid="";
declare -a outFiles;

function cleanup {
  kill $SDRTERM_PID;
  kill $mainPid;
  kill "${pids[@]}";
  i="\0";
  set -u;
  for i in "${!logFiles[@]}"; do
    while IFS= ; read -r line; do
      log "${line}";
    done < ${logFiles["$i"]}
    rm "${logFiles[$i]}";
  done
  unset i;

  i="\0";
  set -u;
  for i in "${outFiles[@]}"; do
      outFilesStr="$(stat -c"%n:%s" ${i})";
      rm -f "${outFilesStr//:44/}";
  done
  unset i;
}

function generateRegex {
  echo "s/^\s*\"*${1}\"*:\s*${2},*\s*$/\1/g"
}

while IFS= ; read -r line; do
  log "${line}"
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
  if [[ ! -z $(echo $line | grep "Started proc Main") ]]; then
    mainPid=$(sed -E "`generateRegex "Started proc Main" "([0-9]+)"`" <<< $line);
    pids[1]=$mainPid;
  fi
  if [[ $line == *"Accepting"* ]]; then
    port=$(echo $line | grep "Accepting" - | sed -E "s/^.*\('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+',\s*([0-9]+)\).*$/\1/g");
    break;
  fi
done <&"${SDR_IN}"

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
  fileName="/tmp/log-${freq}-${ts}";
  outFile="${OUT_PATH}/out-${freq}-${ts}.wav"
  set -u;
  cmd="socat TCP4:${host}:${port} - | sox -q -D -B -traw -b64 -ef -r${decimatedFs} - -traw -b16 -es -r48k - 2>/dev/null | ${DSD_CMD} -w ${outFile} 2>${fileName}"
  set -u;

  log "${cmd}";
  eval "coproc ${coprocName} { ${cmd}; }"
  eval "exec {tmp_in}<&\${${coprocName}[0]}- {tmp_out}>&\${${coprocName}[1]}-";
  eval "pids[\"${coprocName}\"]=\${${coprocName}_PID}";
  logFiles["${coprocName}"]=${fileName};
  outFiles+=(${outFile});

  unset fileName;
  unset cmd;
  unset freq;
  unset coprocName;
  unset tmp_in;
  unset tmp_out;
  sleep 0.1; #TODO figure out a better way to sync this
done
unset i;

while IFS= ; read -r line; do
  log "${line}"
  if [[ $line == *"established"* ]]; then
    break;
  fi
done <&"${SDR_IN}"

trap cleanup EXIT;

log "Awaiting sdrterm";
wait $SDRTERM_PID;
log "sdrterm returned: ${?}";
exit;
