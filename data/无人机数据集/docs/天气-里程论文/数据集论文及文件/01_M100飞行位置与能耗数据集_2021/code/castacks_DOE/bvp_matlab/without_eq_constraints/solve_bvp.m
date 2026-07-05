function [curv_coeffs, sf, perf] = solve_bvp(X0, Xf, v, vw_x, vw_y, dyn_constraints, params)
    % read optimization params
    num_coeffs = params.num_curv_coeffs;
    num_constraints = params.num_constraints;
    t = params.t;
    L = params.L;
    
    % initialize params
    q = init_params(X0, Xf, num_coeffs, v, vw_x, vw_y);
    perf.q_vals = zeros(params.max_iter + 1, num_coeffs);
    perf.cost_vals = zeros(params.max_iter+1, 1);
    perf.endpoint_violation = zeros(params.max_iter+1, 4);
    
    perf.q_vals(1, :) = q;
    perf.cost_vals(1) = obj_fn(q, X0, Xf, L, v, vw_x, vw_y);
    perf.endpoint_violation(1, :) = val_eq_constraint(q, X0, Xf, vw_x, vw_y, v); 
    
    barr_obj = barrier_obj(q, X0, Xf, L, v, vw_x, vw_y, t);
    [q, perf] = solve_barrier(q, X0, Xf, v, vw_x, vw_y, dyn_constraints, params, perf, t);
    barr_obj = barrier_obj(q, X0, Xf, L, v, vw_x, vw_y, t);
    
    idx = 2;
    while params.m / t > params.barr_eps
        t = params.mu * t;
        [q, perf] = solve_barrier(q, X0, Xf, v, vw_x, vw_y, dyn_constraints, params, perf, t);
        perf.cost_vals(idx) = obj_fn(q, X0, Xf, L, v, vw_x, vw_y);
        perf.endpoint_violation(idx, :) = val_eq_constraint(q, X0, Xf, vw_x, vw_y, v); 
        perf.q_vals(idx, :) = q;
        idx = idx + 1;
    end
    
    curv_coeffs = [fliplr(q(1:end-1)'), 0];
    sf = q(end);
end