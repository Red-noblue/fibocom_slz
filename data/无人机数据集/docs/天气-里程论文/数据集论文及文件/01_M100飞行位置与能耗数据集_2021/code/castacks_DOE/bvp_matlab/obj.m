function [o,g] = obj(q)
%o = norm(err(p,XF,sf));
%g = err_grad(p,XF,sf);
o = q(end);
g = zeros(size(q,2),1);
g(end) = 1;
end

