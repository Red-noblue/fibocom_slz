function [obj_val, grad] = obj_fn_with_gradient(q, X0, Xf, v, vw_x, vw_y, params)
    obj_val = obj_fn(q, X0, Xf, v, vw_x, vw_y, params);
    grad_anal = get_gradient(q, params.num_poly_params, X0, Xf, params.L, v, vw_x, vw_y, params.lambda);
    
%     fn = @(q_params) obj_fn(q_params, X0, Xf, v, vw_x, vw_y, params);
%     grad_fd = finite_dif(fn, q);
    grad = grad_anal;
%     grad = grad_fd;
%     grad = grad' / norm(grad);
end