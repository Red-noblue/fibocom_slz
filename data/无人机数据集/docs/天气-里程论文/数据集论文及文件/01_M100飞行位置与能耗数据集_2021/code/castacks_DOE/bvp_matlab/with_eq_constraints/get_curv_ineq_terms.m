function [A, grad] = get_curv_ineq_terms(q, params)
    % get ineq values
    A = params.A_init * q - params.b_init;
    
    % get gradient terms
    grad = zeros(size(A, 1), length(q));
    for i = 1:length(q)
        grad(:, i) = params.A_init(:, i);
    end
end