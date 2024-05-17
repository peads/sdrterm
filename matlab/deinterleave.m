function [a, b] = deinterleave(in, varargin, NameValueArgs)
    arguments
        in
    end
    arguments (Repeating)
         varargin
    end
    arguments
        NameValueArgs.matrixOut = false;
    end

    if (nargin == 1)
        fun = @(start, x)(@(x) x(start:2:end));
        % funA = @(x) x(1:2:end);
        funA = fun(1);
        funB = fun(2);
    elseif (nargin ~= 3)
        throw(MException('MyComponent:noSuchVariable', '1 or 3 input parameters expected. Got: %d, the latter two must be function handles used to produce the output parameters a and b respectively', nargin))
    else
        funA=varargin{1};
        funB=varargin{2};
    end

    a = funA(in);
    b = funB(in);

    if (NameValueArgs.matrixOut)
        a = [a b];
        b = [];
    end
end
