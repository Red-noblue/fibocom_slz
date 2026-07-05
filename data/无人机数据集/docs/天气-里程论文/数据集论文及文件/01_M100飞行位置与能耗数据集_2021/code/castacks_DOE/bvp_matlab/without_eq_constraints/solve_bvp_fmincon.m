function [curv_coeffs, sf, perf] = solve_bvp_fmincon(X0, Xf, v, vw_x, vw_y, dyn_constraints, params)
    perf = [];
    num_coeffs = params.num_curv_coeffs;
    q0 = init_params(X0, Xf, num_coeffs, v, vw_x, vw_y, params);
    
    lb = zeros(num_coeffs, 1) - 1;
    ub = zeros(num_coeffs, 1) + 1;
    lb(end) = 1;
    ub(end) = 20;
    opts = optimoptions('fmincon', 'GradObj', 'on', 'DerivativeCheck', 'off', 'Display', 'iter-detailed');
    fun = @(p) obj_fn_with_gradient(p, X0, Xf, params.L, v, vw_x, vw_y);
    
    q = fmincon(fun, q0, [], [], [], [], lb, ub, [], opts);
    
    curv_coeffs = [fliplr(q(1:end-1)'), 0];
    sf = q(end);
    val_eq_constraint(q, X0, Xf, vw_x, vw_y, v)
end