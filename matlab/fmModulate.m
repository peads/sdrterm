close all;
clear -regexp '\<(?!inFileName\>)\w*';

fileName = 'LRMonoPhase4.bin';
if (exist('inFileName', 'var'))
    fileName = inFileName;
end
fs = 1024000;
fid = fopen(fileName, 'r');
x = fread(fid, 'float');
fclose(fid);
x = single(x);
x = x(1:length(x) - (length(x)/fs - floor(length(x)/fs))*fs);
y = deinterleave(x, matrixOut=true);

fmbMod = comm.FMBroadcastModulator(AudioSampleRate=fs/4, ...
                                   Stereo=1, ...
                                   SampleRate=fs/4);
fmbDemod = MyFMBroadcastDemodulator(fmbMod);

saFM = spectrumAnalyzer(SampleRate=fs, ...
                        ChannelNames=["FM" "Shifted"], ...
                        Title="FM Broadcast Signal");
saAudio = spectrumAnalyzer(SampleRate=fs, ...
                           ShowLegend=true, ...
                           Title="Audio Signal", ...
                           ChannelNames=["Input signal" "Demodulated signal" "File signal"]);

z = fmbMod(y);
a = real(z);
b = imag(z);
out = interleave(a, b);
saFM(z);
z = fmbDemod(z);
figure;
plot(z);

fileName = ['out-' num2str(fmbMod.AudioSampleRate,'%d') '.bin'];
fid = fopen(fileName, 'w');
fwrite(fid, out, 'float');
fclose(fid);

fid = fopen(fileName, 'r');
in = single(fread(fid, 'float'));
fclose(fid);

assert(numel(in) == numel(out) && 1 == numel(out)/sum(in==out))

[re, im] = deinterleave(in);
in = complex(re, im);
fmbDemod.release();
z = fmbDemod(in);
figure;
plot(z);
