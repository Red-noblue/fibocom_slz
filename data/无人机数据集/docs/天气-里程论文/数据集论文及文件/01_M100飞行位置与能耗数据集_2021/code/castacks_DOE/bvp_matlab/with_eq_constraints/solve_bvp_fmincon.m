function [q, perf] = solve_bvp_fmincon(X0, Xf, Xf_orig, v, vw_x, vw_y, params, seed, algo)

% initialize
num_coeffs = params.num_curv_coeffs;
if exist('seed','var') && seed(1) ~= 1
    q0 = seed;
else
    [q0, dub_path] = init_params(X0, Xf, Xf_orig, num_coeffs, v, vw_x, vw_y, params);
    perf.dub_path = dub_path;
end
if ~exist('algo','var')
    algo = 'interior-point';
end

num_params = length(q0);
perf.q0 = q0;

bounds = 1e-2*[params.scales; params.scales; 0; 0; 0];
% set bounds
lb = zeros(num_params, 1) - bounds;
ub = zeros(num_params, 1) + bounds;
lb(end) = 0;
lb(end-1) = 0;
lb(end-2) = 0;
ub(end) = q0(end) * 2;
ub(end-1) = q0(end-1) * 2;
ub(end-2) = q0(end-2) * 2;

% set constraints
[A, b] = get_constraint_terms(q0, params);
params.A_init = A;
params.b_init = b;

% set up nonlinear constraints function
fun_nonlin = @(q) nonlcon_with_grad_sincos(q, X0, Xf, v, vw_x, vw_y, params);
fun = @(p) obj_fn_with_grad(p, X0, Xf, v, vw_x, vw_y, params);

opts = optimoptions('fmincon', 'GradObj', 'on', 'GradConstr','on', 'Display', 'off',...
    'Algorithm', algo);


q = fmincon(fun, q0, [], [], [], [], lb, ub, fun_nonlin, opts);



end