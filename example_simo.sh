#!/bin/bash

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

cmd="python src/sdrterm.py -c${offset} -t${tuned} --plot=ps --vfos=${vfos} -vv --correct-iq -r${fs} -eB --simo --decimation=${decimation} -w5000 2>&1 0<&${SOCAT_IN}";
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

pipes=();
pids=();
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
  fileName="/tmp/log-${freq}";
  logFiles=("${logFiles[@]}" "$fileName");
  cmd="socat TCP4:localhost:${port} - | sox -q -v0.8 -D -B -traw -b64 -ef -r${decimatedFs} - -traw -b16 -es -r48k - 2>/dev/null | dsd -i - -n -f1 -w ${outPath}/out-${freq}.wav 2>&1 > ${fileName};"
  set -u;
  echo "LOG: ${cmd}";
  coproc { eval "$cmd"; }
  exec {tmp_in}<&${COPROC[0]}- {tmp_out}>&${COPROC[1]}-
  pipes=(${pipes[@]} tmp_in);
  pipes=(${pipes[@]} tmp_out);
  pids=(${pids[@]} COPROC_PID);
  unset freq;
  unset cmd;
  unset tmp_in;
  unset tmp_out;
done
unset i;
echo "$pipes";
echo "$pids";

while IFS= ; read -r line; do
  echo "LOG: ${line}"
  if [[ $line == *"established"* ]]; then
    break;
  fi
done <&"${SDR_IN}"

wait $SDRTERM_PID;
i="\0";
set -u;
for i in "${logFiles[@]}"; do
  printf "\n${i}\n";
#  sh -c "grep -v 'Sync:' ${i}";
  cat $i;
done
unset i;
