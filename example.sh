#!/bin/bash
outPath=/mnt/d
time sox -D -twav ${1} -traw -B - \
  | python src/sdrterm.py --correct-iq -m5000 -eh -r48000 ${2} \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -i - -o /dev/null -n -w ${outPath}/out.wav;
time python src/sdrterm.py -X -i ${1} --correct-iq -m5000 ${2} \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -i - -o /dev/null -n -w ${outPath}/out1.wav;
