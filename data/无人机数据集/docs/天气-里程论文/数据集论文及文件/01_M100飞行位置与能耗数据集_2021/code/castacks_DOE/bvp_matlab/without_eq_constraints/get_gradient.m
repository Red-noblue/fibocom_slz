function [grad, grad_terms] = get_gradient(q, X0, Xf, L, v, vw_x, vw_y, t)
    %% extract params
    sf = q(end);
    p = [X0(4); q(1:end-1)]; % add in a = 0
    curv_coeffs = fliplr(p'); % follow matlab convention for polynomial coeffs
    psi_coeffs = polyint(curv_coeffs, X0(3));
    
    %% compute gradient
    grad = zeros(1, length(q));
    err_term = terminal_error(q, X0, Xf, L, v, vw_x, vw_y);
    grad_terms = zeros(4, length(q));
    
    % set up functions
    fun_cosns = @(s, pow) (s .^ pow) .* cos(polyval(psi_coeffs, s));
    fun_sinns = @(s, pow) (s .^ pow) .* sin(polyval(psi_coeffs, s));
    
    % for cost
%     grad(end) = t;
    
    % for barrier term
%     grad(end) = grad(end) - 1 / (t*sf);
    
    % for end-point error term
    for i = 2:length(q)
%         grad_terms(1, i-1) = -comp_sns(psi_coeffs, sf, i) / i;
%         grad_terms(2, i-1) = comp_cns(psi_coeffs, sf, i) / i;
        grad_terms(1, i-1) = -simpson_integration(fun_sinns, i, 101, 0, sf) / i;
        grad_terms(2, i-1) = simpson_integration(fun_cosns, i, 101, 0, sf) / i;
        grad_terms(3, i-1) = (sf^i) / i;
        grad_terms(4, i-1) = sf ^ (i-1);
        grad(i-1) = grad(i-1) + 1 * (...
            err_term(1) * grad_terms(1, i-1) + ...
            err_term(2) * grad_terms(2, i-1) + ...
            L^2 * err_term(3) * grad_terms(3, i-1) + ...
            L^4 * err_term(4) * grad_terms(4, i-1) );
    end
    grad_terms(1, end) = cos(wrapTo2Pi(polyval(psi_coeffs, sf))) + vw_x / v;
    grad_terms(2, end) = sin(wrapTo2Pi(polyval(psi_coeffs, sf))) + vw_y / v;
    grad_terms(3, end) = polyval(curv_coeffs, sf);
    grad_terms(4, end) = polyval(polyder(curv_coeffs), sf);
    grad(end) = grad(end) + 1 * (...
        err_term(1) * grad_terms(1, end) + ...
        err_term(2) * grad_terms(2, end) + ...
        L^2 * err_term(3) * grad_terms(3, end) + ...
        L^4 * err_term(4) * grad_terms(4, end) );
end