clear all 
close all
t = 45;
%XF = [100*cosd(t) , 100*sind(t) , 0];
XF = [36.4072 , 0 , 0];
p0 = [0 0.1 0 0.9];
sf0 = 0.4;
[A,b] = get_constraint(p0,sf0*4);
q0 = [p0 sf0];
dd(p0,sf0)
lb = zeros(5,1) - 1;
lb(end) = 0;
ub = zeros(5,1) + 1;
ub(end) = 4*sf0;
scatter(XF(1),XF(2))
nonlcon = @(p) boundary(p,XF);
opts = optimoptions('fmincon', 'GradObj', 'on', 'DerivativeCheck', 'off','Display','iter-detailed','SpecifyConstraintGradient',true,'StepTolerance',);
fun = @(q) obj(q);
q = fmincon(fun, q0, A, b, [], [], lb, ub, nonlcon, opts);
q(end)
dd(q(1:end-1),q(end))
