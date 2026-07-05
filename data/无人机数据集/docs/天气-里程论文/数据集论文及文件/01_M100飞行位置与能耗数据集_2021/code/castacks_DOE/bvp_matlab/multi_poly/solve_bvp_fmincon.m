function [q, perf] = solve_bvp_fmincon(X0, Xf, v, vw_x, vw_y, dyn_constraints, params)
    
    % initialize
    num_coeffs = params.num_curv_coeffs;
    [q0, dub_path] = init_params(X0, Xf, num_coeffs, v, vw_x, vw_y, params);
    num_params = length(q0);
    perf.q0 = q0;
    perf.dub_path = dub_path;
    
    % set bounds
    lb = zeros(num_params, 1) - 1;
    ub = zeros(num_params, 1) + 1;
    lb(end) = 0;
    lb(end-1) = 0;
    lb(end-2) = 0;
    ub(end) = q0(end) * 2;
    ub(end-1) = q0(end-1) * 2;
    ub(end-2) = q0(end-2) * 2;
    
    % set constraints
    [A, b] = get_constraint_terms(q0, params);
    
    opts = optimoptions('fmincon', 'GradObj', 'on', 'DerivativeCheck', 'off', 'Display', 'iter-detailed');
    fun = @(p) obj_fn_with_gradient(p, X0, Xf, v, vw_x, vw_y, params);
    
    q = fmincon(fun, q0, A, b, [], [], lb, ub, [], opts);
%     q = q0;
end