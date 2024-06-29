#!/bin/bash
outPath=/mnt/d
echo "START basic raw stdin test";
time sox -D -twav ${1} -traw -B - 2>/dev/null \
  | python src/sdrterm.py --correct-iq -w5000 -eh -r48000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out0.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END basic raw stdin test\n\n";
echo "START basic raw int32 stdin test";
time sox -D -twav ${1} -traw -b32 -B - 2>/dev/null \
  | python src/sdrterm.py --correct-iq -w5000 -ei -r48000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out1.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END basic raw float stdin test\n\n";
time sox -D -twav ${1} -traw -b32 -ef -B - 2>/dev/null \
  | python src/sdrterm.py --correct-iq -w5000 -ef -r48000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out2.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END basic raw float stdin test\n\n";
echo "START basic raw double stdin test";
time sox -D -twav ${1} -traw -b64 -ef -B - 2>/dev/null \
  | python src/sdrterm.py --correct-iq -w5000 -ed -r48000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out3.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END basic raw double stdin test\n\n";

echo "START basic wave file test";
time python src/sdrterm.py -X -i ${1} --correct-iq -w5000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out4.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END basic wave file test\n\n";
echo "START uint8 wave file test";
sox -q -D -twav ${1} -twav -eunsigned-int -b8 /tmp/tmp.wav 2>/dev/null;
time python src/sdrterm.py -X -i ${1} --correct-iq -w5000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out4.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END uint8 wave file test\n\n";
echo "START int32 wave file test";
sox -q -D -twav ${1} -twav -es -b32 /tmp/tmp.wav 2>/dev/null;
time python src/sdrterm.py -X -i ${1} --correct-iq -w5000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out4.wav | grep "Total" - | grep -E --color=always '[0-9]+' -
printf "END int32 wave file test\n\n";
echo "START float wave file test";
sox -q -D -twav ${1} -twav -ef -b32 /tmp/tmp.wav 2>/dev/null;
time python src/sdrterm.py -X -i ${1} --correct-iq -w5000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out4.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END float wave file test\n\n";
echo "START double wave file test";
sox -q -D -twav ${1} -twav -ef -b64 /tmp/tmp.wav 2>/dev/null;
time python src/sdrterm.py -X -i ${1} --correct-iq -w5000 ${2} 2>/dev/null \
  | sox -q -D -v0.75 -traw -r24k -b64 -ef - -traw -r48k -b16 -es - 2>/dev/null \
  | dsd -q -i - -o /dev/null -n -w ${outPath}/out4.wav | grep "Total" - | grep -E --color=always '[0-9]+' -;
printf "END double wave file test\n\n";
rm -f /tmp/tmp.wav;
