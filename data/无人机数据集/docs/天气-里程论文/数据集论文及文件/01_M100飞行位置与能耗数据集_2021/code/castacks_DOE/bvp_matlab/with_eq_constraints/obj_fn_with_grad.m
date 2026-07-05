function [obj_val, grad] = obj_fn_with_grad(q, X0, Xf, v, vw_x, vw_y, params)
    obj_val = obj_fn(q);
    
    grad = get_grad_cost(q, X0, Xf, v, vw_x, vw_y, params);
end