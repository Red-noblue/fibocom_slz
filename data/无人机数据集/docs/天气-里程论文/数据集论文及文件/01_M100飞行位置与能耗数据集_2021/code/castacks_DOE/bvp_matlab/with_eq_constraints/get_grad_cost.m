function [grad] = get_grad_cost(q, X0, Xf, v, vw_x, vw_y, params)
    grad = zeros(1, length(q));
    sf = sum(q(end-2:end));
    
%     grad(end-2) = sf;
%     grad(end-1) = sf;
%     grad(end) = sf;
    grad(end-2) = 1;
    grad(end-1) = 1;
    grad(end) = 1;
end