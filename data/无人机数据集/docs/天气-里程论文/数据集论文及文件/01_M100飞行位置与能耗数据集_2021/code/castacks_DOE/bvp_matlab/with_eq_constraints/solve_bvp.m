function [curv_coeffs, sf, perf] = solve_bvp(X0, Xf, v, vw_x, vw_y, dyn_constraints, params)
    % read optimization params
    num_coeffs = params.num_curv_coeffs;
    num_constraints = params.num_constraints;
    
    % initialize params
    [q, lambda] = init_params(X0, Xf, num_coeffs, v, vw_x, vw_y);
    perf.q_vals = zeros(params.max_iter + 1, num_coeffs + 1);
    perf.lambda_vals = zeros(params.max_iter + 1, 4);
    perf.cost_vals = zeros(params.max_iter+1, 1);
    perf.endpoint_violation = zeros(params.max_iter+1, 4);
    
    perf.q_vals(1, :) = q;
    perf.lambda_vals(1, :) = lambda;
    perf.cost_vals(1) = obj_fn(q);
    perf.endpoint_violation(1, :) = val_eq_constraint(q, X0, Xf, vw_x, vw_y, v); 
    % optimize!
    for i = 1:params.max_iter
        i
        % compute gradients and hessians
        hess = hessian_lagrangian(q, lambda, X0, vw_x, vw_y, v);
        grad_eq_constr = gradient_eq_constraint(q, X0, vw_x, vw_y, v);
        grad_lagrangian = gradient_lagrangian(q, lambda, X0, vw_x, vw_y, v);
        eq_constr = val_eq_constraint(q, X0, Xf, vw_x, vw_y, v);
        
        % determine params update
        lhs = [hess, grad_eq_constr'; ...
            grad_eq_constr, zeros(num_constraints, num_constraints)];
        rhs = [-grad_lagrangian'; -eq_constr];
        del_params = lhs \ rhs;
        
        % backtrack to find the right step size
        t = 1;
        curr_residual = norm(get_residual(q, lambda, X0, Xf, v, vw_x, vw_y));
        while true
            temp_q = q + t*del_params(1:length(q));
            temp_lambda = lambda + t*del_params(length(q)+1:end);
            if norm(get_residual(temp_q, temp_lambda, X0, Xf, v, vw_x, vw_y)) > (1 - params.alpha*t) * curr_residual || temp_q(end) < 0
                t = params.beta * t;
            else
                q = q + t*del_params(1:length(q));
                lambda = lambda + t*del_params(length(q)+1:end);
                break;
            end
        end
        
        % log stuff
        perf.q_vals(i+1, :) = q;
        perf.lambda_vals(i+1, :) = lambda;
        perf.cost_vals(i+1) = obj_fn(q);
        perf.endpoint_violation(i+1, :) = val_eq_constraint(q, X0, Xf, vw_x, vw_y, v); 
    end
    
    curv_coeffs = fliplr(q(1:end-1)');
    sf = q(end);
end