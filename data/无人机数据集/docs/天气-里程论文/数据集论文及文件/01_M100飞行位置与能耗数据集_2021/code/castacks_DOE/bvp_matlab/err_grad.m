function [g] = err_grad(p,XF ,sf)
e = err(p,XF,sf);
psi = polyint(p);
S = @(s,n) (s.^n).*sin(polyval(psi,s))/n;
C = @(s,n) (s.^n).*cos(polyval(psi,s))/n;

for i = 1:size(p,2) 
    grad_psi(i) =  (sf^i)/i;
    grad_x(i) = -integral(@(s) S(s,i), 0 , sf);
    grad_y(i) = integral(@(s) C(s,i), 0 , sf);
end
g = e(1)*grad_x + e(2)*grad_y + e(3)*grad_psi;
end

