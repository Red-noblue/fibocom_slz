clear all 
close all
t = 45;
%XF = [100*cosd(t) , 100*sind(t) , 0];
XF = [3.4072 , 4 , 0];
sf0 = 100;
s = sf0;
A = [0 0 1 s s^2 s^3; 0 1 s s^2/2 s^3/3 s^4/4; 1 s s^2/2 s^3/6 s^4/12 s^5/20; 0 0 1 0 0 0; 0 1 0 0 0 0; 1 0 0 0 0 0];
A = fliplr(A);
xf = [0 cos(XF(3)) XF(1) 0 1 0]';
x = inv(A)*xf;
yf = [0 sin(XF(3)) XF(2) 0 0 0]';
y = inv(A)*yf;
X = [x(1)/20 x(2)/12 x(3)/6 x(4)/2 x(5) x(6)];
Y = [y(1)/20 y(2)/12 y(3)/6 y(4)/2 y(5) y(6)];
j = 0;
for i = 1:s/0.01
    x_(i) = polyval(X,j); 
    y_(i) = polyval(Y,j); 
    j = j + 0.01;
end
plot(x_,y_)
hold on
