function [val] = obj_fn(q, X0, Xf, v, vw_x, vw_y, params)
    sf1 = q(end-2);
    c1 = fliplr([X0(4); q(1:params.num_poly_params)]'); % follow matlab poly convention
    cf1 = polyval(c1, sf1);
    err_term = terminal_error(q, params.num_poly_params, X0, Xf, params.L, v, vw_x, vw_y);
    
    val = 0.5 * norm(err_term)^2 + 0.5 * params.lambda * cf1^2;
end