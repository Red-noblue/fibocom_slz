% clear all
% close all
% p = [41.5 -82 33 0];
% sf = 1.5;
% dd(p,sf);
% l = 2;
% p = [p(1)/l^4 p(2)/l^3 p(3)/l^2 p(4)/l];
% sf = 1.5*l;
% dd(p,sf)
function a = dd(p,sf)
theta = [p(1)/4 p(2)/3 p(3)/2 0 0];
x = 0;
y = 0;
i = 0;
for s = 0:0.01:sf
    i = i + 1;
    t = polyval(theta , s);
    x(i+1) = x(i) + cos(t);
    y(i+1) = y(i) + sin(t);
end
% x(end)
% y(end)
% t
plot(x,y)
hold on
end

