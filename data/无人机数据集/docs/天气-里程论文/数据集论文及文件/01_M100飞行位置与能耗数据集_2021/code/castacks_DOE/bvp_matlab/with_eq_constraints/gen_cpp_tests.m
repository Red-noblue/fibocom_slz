clear; clc; close all
%% initialize
% define params
params.num_curv_coeffs = 5;
params.num_poly_params = params.num_curv_coeffs - 1;
params.num_constraints = 4;
params.num_samples = 100;
params.num_constraint_samples = 50;
params.max_kappa = 1/20;
params.max_kappa_rate = params.max_kappa;
params.bv_tol = [1e-1; 1e-1; 1e-3; 1e-4];
params.bv_tol_sincos = [1e-3; 1e-3; 1e-3; 1e-3; 1e-4];
params.curv1_tol = 1e-4;
num_poly_params = params.num_poly_params;

% define scaling factors
params.scale_factor = 1;
params.scales = zeros(params.num_poly_params, 1);
for i = 1:params.num_poly_params
   params.scales(i) =  params.scale_factor^i;
end

% define speeds
v = 50;
vw_x = 0;
vw_y = 0;

% define boundary values (x, y, psi, curv)
X0 = [0, 0, 0, 0];
Xf = [60, 70, pi/2, 0];
% Xf = [70, 80, pi/2, 0];

% convert groundframe heading into airframe heading
Xf_orig = Xf;
Xf(3) = get_airframe_heading(v, Xf(3), vw_x, vw_y);

% define dynamics constraints
dyn_constraints = [];

%% generate stuff to compare against
% get initial guess
% [q, ~] = init_params(X0, Xf, Xf_orig, params.num_curv_coeffs, v, vw_x, vw_y, params);
% dlmwrite('~/dump/kite/q0.txt', q);
q = dlmread('~/dump/kite/q0.txt');

% scale poly coeffs
q(1:num_poly_params) = q(1:num_poly_params) ./ params.scales;
q(num_poly_params+1:2*num_poly_params) = q(num_poly_params+1:2*num_poly_params) ./ params.scales;

% extract params
sf1 = q(end-2);
sf2 = q(end-1);
sf3 = q(end);
c1 = fliplr([X0(4); q(1:num_poly_params)]'); % follow matlab poly convention
c2 = [zeros(1, num_poly_params), polyval(c1, sf1)]; % follow matlab poly convention
c3 = fliplr([polyval(c2, sf2); q(num_poly_params+1:end-3)]'); % follow matlab poly convention
psi1 = polyint(c1, X0(3));
psi2 = polyint(c2, polyval(psi1, sf1));
psi3 = polyint(c3, polyval(psi2, sf2));
c1_f = polyval(c1, sf1);
c1_df = polyval(polyder(c1), sf1);
psi_f = polyval(psi3, sf3);
cos_f = cos(psi_f);
sin_f = sin(psi_f);

% get linear ineq terms
[A, b] = get_constraint_terms(q, params);
params.A_init = A;
params.b_init = b;
[A_curv, grad_curv] = get_curv_ineq_terms(q, params);
grad_curv = grad_curv';
dlmwrite('~/dump/kite/A_ineq.txt', A_curv);
dlmwrite('~/dump/kite/grad_ineq.txt', grad_curv(:));

% generate sin/cos caches
fun_sinns1 = @(s, pow) (s .^ pow) .* sin(polyval(psi1, s));
fun_sinns2 = @(s, pow) (s .^ pow) .* sin(polyval(psi2, s));
fun_sinns3 = @(s, pow) (s .^ pow) .* sin(polyval(psi3, s));
fun_cosns1 = @(s, pow) (s .^ pow) .* cos(polyval(psi1, s));
fun_cosns2 = @(s, pow) (s .^ pow) .* cos(polyval(psi2, s));
fun_cosns3 = @(s, pow) (s .^ pow) .* cos(polyval(psi3, s));
c1_cos_cache = zeros(params.num_poly_params+2, 1);
c2_cos_cache = zeros(params.num_poly_params+2, 1);
c3_cos_cache = zeros(params.num_poly_params+2, 1);
c1_sin_cache = zeros(params.num_poly_params+2, 1);
c2_sin_cache = zeros(params.num_poly_params+2, 1);
c3_sin_cache = zeros(params.num_poly_params+2, 1);
for i = 0:params.num_poly_params+1
    c1_cos_cache(i+1) = simpson_integration(fun_cosns1, i, 101, 0, sf1);
    c2_cos_cache(i+1) = simpson_integration(fun_cosns2, i, 101, 0, sf2);
    c3_cos_cache(i+1) = simpson_integration(fun_cosns3, i, 101, 0, sf3);
    c1_sin_cache(i+1) = simpson_integration(fun_sinns1, i, 101, 0, sf1);
    c2_sin_cache(i+1) = simpson_integration(fun_sinns2, i, 101, 0, sf2);
    c3_sin_cache(i+1) = simpson_integration(fun_sinns3, i, 101, 0, sf3);
end
dlmwrite('~/dump/kite/c1_cos_cache.txt', c1_cos_cache);
dlmwrite('~/dump/kite/c2_cos_cache.txt', c2_cos_cache);
dlmwrite('~/dump/kite/c3_cos_cache.txt', c3_cos_cache);
dlmwrite('~/dump/kite/c1_sin_cache.txt', c1_sin_cache);
dlmwrite('~/dump/kite/c2_sin_cache.txt', c2_sin_cache);
dlmwrite('~/dump/kite/c3_sin_cache.txt', c3_sin_cache);

% generate simpson weights
weights = [1, 4, repmat([2, 4], 1, (101-3)/2), 1];
dlmwrite('~/dump/kite/simpson.txt', weights);

% generate pow terms
pow_terms = zeros(params.num_poly_params+2, 2);
for i = 0:params.num_poly_params+1
    pow_terms(i+1, 1) = sf1^i;
    pow_terms(i+1, 2) = sf3^i;
end
dlmwrite('~/dump/kite/pow.txt', pow_terms);

% generate terminal error
err = terminal_error_sincos(q, params.num_poly_params, X0, Xf, v, vw_x, vw_y, params);
dlmwrite('~/dump/kite/terminal_error.txt', err);