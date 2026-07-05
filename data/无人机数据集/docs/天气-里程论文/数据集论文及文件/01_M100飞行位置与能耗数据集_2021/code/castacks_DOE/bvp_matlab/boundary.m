function [c,ceq, cgrad, ceqgrad] = boundary(q,XF)
sf = q(end);
p = q(1:end-1);

c = [];
cgrad = [];

theta = polyint(p);
L = 4;
XF(3) = (L^2)*XF(3);
xf(3) = (L^2)*polyval(theta,sf);
x = @(s) cos(polyval(theta,s));
y = @(s) sin(polyval(theta,s));
xf(1) =  integral(x, 0 ,sf);
xf(2) =  integral(y, 0 ,sf);
ceq = xf - XF;

psi = polyint(p);
S = @(s,n) (s.^n).*sin(polyval(psi,s))/n;
C = @(s,n) (s.^n).*cos(polyval(psi,s))/n;

for i = size(p,2):-1:1 
    grad_psi(i) =  (sf^i)/i;
    grad_x(i) = -integral(@(s) S(s,i), 0 , sf);
    grad_y(i) = integral(@(s) C(s,i), 0 , sf);
end
%keyboard
e = [1,1,1];
%e = (e);
g(:,1) = e(1)*grad_x ;
g(:,2) = e(2)*grad_y ;
g(:,3) = (L^2)*e(3)*grad_psi;
ceqgrad = flipud(g);
ceqgrad(5,3) = (L^2)*e(3)*polyval(p,sf);
ceqgrad(5,2) = e(2)*sin(polyval(psi,sf));
ceqgrad(5,1) = e(1)*cos(polyval(psi,sf));

end

