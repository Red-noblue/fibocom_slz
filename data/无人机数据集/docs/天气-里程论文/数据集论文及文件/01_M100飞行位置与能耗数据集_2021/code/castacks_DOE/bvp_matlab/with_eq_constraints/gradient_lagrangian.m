function [grad] = gradient_lagrangian(q, lambda, X0, vw_x, vw_y, v)
    grad = zeros(length(q), 1);
    
    % gradient for cost function (= sf)
    grad(end) = 1;
    
    % add in gradient for constraints scaled by lambda
    grad = grad' + lambda' * gradient_eq_constraint(q, X0, vw_x, vw_y, v);
end