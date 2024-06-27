#!/bin/bash

inFile=""
outPath=/mnt/d
decimation=50;
offset="-3.5E+5";
fs=1024000;
vfos=(15000 -60000 52500);
logFiles=();
tuned=0

if [[ ! -z "$1" ]]; then
  inFile="-i ${1}"
fi

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
  IFS=', ' read -r -a vfos <<< "$6"
fi

cmd="python src/sdrterm.py -X ${inFile} -c${offset} -t${tuned} --vfos=$(IFS=, ; echo "${vfos[*]}") --correct-iq -r${fs} -eB --simo --decimation=${decimation} -m5000 2>&1";
echo "LOG: ${cmd}"
coproc SDRTERM { eval "$cmd"; }

port="";
decimatedFs="";
while IFS= read -r line; do
  echo "LOG: ${line}"
  if [[ ! -z "$(echo $line | grep "decimatedFs" -)" ]]; then
    decimatedFs=$(echo $line | sed -E "s/^\"decimatedFs\":\s+([0-9]+)$/\1/g");
  fi
  if [[ $line == *"Accepting"* ]]; then
    port=$(echo $line | grep "Accepting" - | sed -E "s/(^.*\('[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+', ([0-9]+)\).*$)/\2/g");
    break;
  fi
done <&"${SDRTERM[0]}"

vfos=(${vfos[@]} "0");
for i in "${vfos[@]}"; do
  fileName="/tmp/log-${i}-$(date +%s%N)";
  logFiles=("${logFiles[@]}" "$fileName");
  cmd="socat TCP4:localhost:${port} - | sox -v0.75 -D -B -traw -b64 -ef -r${decimatedFs} - -traw -b16 -es -r48k - 2>/dev/null | dsd -i - -o /dev/null -n -f1 -w ${outPath}/out-${i}.wav > ${fileName};"
  echo "LOG: ${cmd}"
  eval "$cmd" &
done

while IFS= read -r line; do
  echo "LOG: ${line}"
  if [[ $line == *"established"* ]]; then
    break;
  fi
done <&"${SDRTERM[0]}"
wait $SDRTERM_PID

for i in "${logFiles[@]}"; do
  printf "\n${i}\n";
  sh -c "grep -v 'Sync:' ${i}";
  rm "$i";
done
