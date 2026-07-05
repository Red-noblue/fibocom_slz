clear; clc; close all

% define params
params.num_curv_coeffs = 5;
params.num_poly_params = params.num_curv_coeffs - 1;
params.num_constraints = 4;
params.num_samples = 100;
params.num_constraint_samples = 50;
params.L = 4;
params.lambda = 5;
params.max_kappa = 1/20;
params.max_kappa_rate = params.max_kappa;

% define speeds
v = 30;
vw_x = 0;
vw_y = 0;

% define boundary values (x, y, psi, curv)
X0 = [0, 0, 0, 0];
% Xf = [34, 21, 0, 0];
Xf = [70, 21, 2*pi/3, 0];

% convert groundframe heading into airframe heading
Xf(3) = get_airframe_heading(v, Xf(3), vw_x, vw_y);

% define dynamics constraints
dyn_constraints = [];

% optimize!
[q, perf] = solve_bvp_fmincon(X0, Xf, v, vw_x, vw_y, dyn_constraints, params);

% plot stuff
plot_stuff(q, X0, Xf, params, v, vw_x, vw_y, perf);

constr_violation(q, params.num_poly_params, X0, Xf, v, vw_x, vw_y)
