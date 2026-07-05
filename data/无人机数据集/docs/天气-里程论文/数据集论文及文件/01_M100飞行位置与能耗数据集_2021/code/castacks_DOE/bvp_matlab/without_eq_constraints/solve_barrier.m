function [q, perf] = solve_barrier(q, X0, Xf, v, vw_x, vw_y, dyn_constraints, params, perf, t)
    L = params.L;
%     old_obj = barrier_obj(q, X0, Xf, L, v, vw_x, vw_y, t);
    old_obj = obj_fn(q, X0, Xf, L, v, vw_x, vw_y);
    
    % newton's iterations
    while true
        [grad, grad_terms] = get_gradient(q, X0, Xf, L, v, vw_x, vw_y, t);
        hess = get_hessian(q, X0, Xf, L, v, vw_x, vw_y, t, grad_terms);
        
        % backtrack
        step_size = 1;
        step = -hess \ grad';
        q_temp = q + step_size * step;
%         while barrier_obj(q_temp, X0, Xf, L, v, vw_x, vw_y, t) > ...
%             (barrier_obj(q, X0, Xf, L, v, vw_x, vw_y, t) + ...
%             params.alpha * step_size * grad * step)
        while obj_fn(q_temp, X0, Xf, L, v, vw_x, vw_y) > ...
            (obj_fn(q, X0, Xf, L, v, vw_x, vw_y) + ...
            params.alpha * step_size * grad * step)
            
            step_size = params.beta * step_size;
            q_temp = q + step_size * step;
        end
        
        q = q_temp;
        new_obj = obj_fn(q, X0, Xf, L, v, vw_x, vw_y);
        if old_obj - new_obj < params.newton_tol
            break;
        end
        
        old_obj = new_obj;
    end
end