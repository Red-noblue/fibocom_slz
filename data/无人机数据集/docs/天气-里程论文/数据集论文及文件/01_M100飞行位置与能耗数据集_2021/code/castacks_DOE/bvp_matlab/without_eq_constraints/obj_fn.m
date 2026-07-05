function [obj] = obj_fn(q, X0, Xf, L, v, vw_x, vw_y)
    obj = 0.5 * norm(terminal_error(q, X0, Xf, L, v, vw_x, vw_y)) ^ 2;
end