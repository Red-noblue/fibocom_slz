function [o] = err(p,XF,sf)
L = 4;
theta = polyint(p);
xf(3) = (L^2)*polyval(theta,sf);
XF(3) = (L^2)*XF(3);
x = @(s) cos(polyval(theta,s));
y = @(s) sin(polyval(theta,s));
xf(1) =  integral(x, 0 ,sf);
xf(2) =  integral(y, 0 ,sf);
o = xf - XF;
end

