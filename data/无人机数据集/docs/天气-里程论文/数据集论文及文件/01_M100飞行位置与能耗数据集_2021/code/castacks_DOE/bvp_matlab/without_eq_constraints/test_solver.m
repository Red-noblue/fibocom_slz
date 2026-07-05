clear; clc; close all

% define optimization and other params
params.max_iter = 100;
params.num_curv_coeffs = 6;
params.num_constraints = 4;
params.num_samples = 100;
params.newton_tol = 1e-3;
params.alpha = 0.2;
params.beta = 0.9;
params.mu = 20;
params.t = 1;
params.m = 1;
params.barr_eps = 1e-9;
params.L = 2;
params.max_kappa = 1/2;
params.max_kappa_rate = params.max_kappa;

% define speeds
v = 30;
vw_x = 0;
vw_y = 0;

% define boundary values (x, y, psi, curv)
X0 = [0, 0, 0, 0];
% Xf = [30, 5, 0.139397290666667, 0.0065715]; % 39.92, 1.73
Xf = [10, 5, 0, 0];

% convert groundframe heading into airframe heading
Xf(3) = get_airframe_heading(v, Xf(3), vw_x, vw_y);

% define dynamics constraints
dyn_constraints = [];

% optimize!
% [curv_coeffs, sf, perf] = solve_bvp(X0, Xf, v, vw_x, vw_y, dyn_constraints, params);
[curv_coeffs, sf, perf] = solve_bvp_fmincon(X0, Xf, v, vw_x, vw_y, dyn_constraints, params);

% plot stuff
plot_stuff(X0, Xf, curv_coeffs, sf, params, v, vw_x, vw_y, perf);