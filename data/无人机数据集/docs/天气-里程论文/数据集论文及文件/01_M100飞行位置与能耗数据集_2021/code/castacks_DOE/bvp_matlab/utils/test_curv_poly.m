clear; clc; close all

degree = 4;
params.num_poly_params = 4;
params.num_samples = 100;
perf = [];

% speeds
v = 30;
vw_x = 1;
vw_y = 3;

% boundary values
X0 = [0, 0, 0, 0];
Xf = [5, 7, 0, 0];

% dynamic limits
dyn.max_kappa = 1/20;
dyn.max_kappa_rate = dyn.max_kappa;

% get dubins solution
[path, l1, l2, l3, curv_type] = dubins_curve(X0(1:3), Xf(1:3), 1/dyn.max_kappa, 1, true);

% check for direction of dubins curves
head_change_1 = l1 * dyn.max_kappa; 
head_change_3 = l3 * dyn.max_kappa;
if curv_type(1) == 3
    head_change_1 = -head_change_1;
end
if curv_type(3) == 3
    head_change_3 = -head_change_3;
end

% set up constraints for curv optimization 1
constraints1.bv = [X0(4); Xf(4)];
constraints1.bv_deriv = [0; 0];
constraints1.bv_heading = [0; head_change_1];
constraints1.curv_max = dyn.max_kappa;
constraints1.curv_rate = dyn.max_kappa_rate;
constraints1.curv_rate_rate = dyn.max_kappa_rate;

% set up constraints for curv optimization 2
constraints3.bv = [X0(4); Xf(4)];
constraints3.bv_deriv = [0; 0];
constraints3.bv_heading = [0; head_change_3];
constraints3.curv_max = dyn.max_kappa;
constraints3.curv_rate = dyn.max_kappa_rate;
constraints3.curv_rate_rate = dyn.max_kappa_rate;

% get curv poly1
[c1, sf1, flag1] = get_curv_poly(degree, constraints1, l1);

% get curv poly3
[c3, sf3, flag3] = get_curv_poly(degree, constraints3, l3);
sf2 = 0.01*l2;

if flag1 && flag3
    q = [fliplr(c1(1:end-1))'; fliplr(c3(1:end-1))'; sf1; sf2; sf3]; 
    curv_path = get_curvpp_path(q, X0, Xf, params, v, vw_x, vw_y, perf);

    % plot stuff
    figure, hold on
    plot(X0(1), X0(2), 'r*');
    plot(Xf(1), Xf(2), 'b*');
    plot(path(:, 1), path(:, 2), 'k-');
    plot(curv_path(:, 1), curv_path(:, 2), 'g-');
    legend('Start', 'Goal', 'Dubins', 'Curv pp');
end



