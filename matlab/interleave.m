function out = interleave(a, b, NameValueArgs)
    arguments
        a
        b
        NameValueArgs.toColumn = true
    end

    a = a(:).';
    b = b(:).';
    out = [a;b];
    out = out(:);
    if (~NameValueArgs.toColumn)
        out = out';
    end
end
