function [barr_obj] = barrier_obj(q, X0, Xf, L, v, vw_x, vw_y, t)
    if q(end) < eps
        barr_obj = Inf;
    else
        barr_obj = t * obj_fn(q, X0, Xf, L, v, vw_x, vw_y) - log(q(end));
    end
end