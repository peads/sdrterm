classdef MyFMBroadcastDemodulator < comm.FMBroadcastDemodulator
   methods
     function obj = MyFMBroadcastDemodulator(varargin)
        if nargin == 1
          coder.internal.errorIf(~isa(varargin{1}, 'comm.FMBroadcastModulator'), ...
                                 'comm:FMModem:WrongObjectFMBCModulator');
          % the 1st input argument is an FM broadcast modulator
          modObj = varargin{1};
          obj.SampleRate = modObj.SampleRate;
          obj.FrequencyDeviation = modObj.FrequencyDeviation;
          obj.FilterTimeConstant = modObj.FilterTimeConstant;
          obj.AudioSampleRate = modObj.AudioSampleRate;
          obj.Stereo = modObj.Stereo;
        else
          setProperties(obj, nargin, varargin{:});
        end
     end
   end
end