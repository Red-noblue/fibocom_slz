function [obj_val, grad] = obj_fn_with_gradient(q, X0, Xf, L, v, vw_x, vw_y)
    obj_val = obj_fn(q, X0, Xf, L, v, vw_x, vw_y);
    [grad_anal, ~] = get_gradient(q, X0, Xf, L, v, vw_x, vw_y, 1);
    
    fn = @(q_params) obj_fn(q_params, X0, Xf, L, v, vw_x, vw_y);
    grad_fd = finite_dif(fn, q);
    grad = grad_anal;
%     grad = grad' / norm(grad);
end