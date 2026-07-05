function [hess] = get_hessian(q, X0, Xf, L, v, vw_x, vw_y, t, grad_terms)
    %% extract params
    num_params = length(q);
    sf = q(end);
    p = [X0(4); q(1:end-1)]; % add in a = 0
    curv_coeffs = fliplr(p'); % follow matlab convention for polynomial coeffs
    psi_coeffs = polyint(curv_coeffs, X0(3));
    
    %% compute some end points
    psi_f = wrapTo2Pi(polyval(psi_coeffs, sf));
    curv_f = polyval(curv_coeffs, sf);
    curv_dash_f = polyval(polyder(curv_coeffs), sf);
    curv_dash_dash_f = polyval(polyder(polyder(curv_coeffs)), sf);
    
    %% compute hessian
    hess = zeros(num_params);
    err_term = terminal_error(q, X0, Xf, L, v, vw_x, vw_y);
    
    % no term for cost, but the barrier function makes a contribution
%     hess(end, end) = hess(end, end) + 1 / (t * sf^2);
    
    % hessian w.r.t x
    for i = 2:num_params
        for j = 2:num_params
            hess(i-1, j-1) = hess(i-1, j-1) - err_term(1) * comp_cns(psi_coeffs, sf, i+j) / (j*i);
        end
        
        hess(end, i-1) = hess(end, i-1) - err_term(1) * (sf^i) * sin(psi_f) / i;
        hess(i-1, end) = hess(i-1, end) - err_term(1) * (sf^i) * sin(psi_f) / i;
    end
    hess(end, end) = hess(end, end) - err_term(1) * curv_f * sin(psi_f);

    % hessian w.r.t y
    for i = 2:num_params
        for j = 2:num_params
            hess(i-1, j-1) = hess(i-1, j-1) - err_term(2) * comp_sns(psi_coeffs, sf, i+j) / (j*i);
        end
        
        hess(end, i-1) = hess(end, i-1) + err_term(2) * (sf^i) * cos(psi_f) / i;
        hess(i-1, end) = hess(i-1, end) + err_term(2) * (sf^i) * cos(psi_f) / i;
    end
    hess(end, end) = hess(end, end) + err_term(2) * curv_f * cos(psi_f);

    % hessian w.r.t psi
    for i = 2:num_params
        hess(end, i-1) = hess(end, i-1) + L^2 * err_term(3) * (sf^(i-1));
        hess(i-1, end) = hess(i-1, end) + L^2 * err_term(3) * (sf^(i-1));
    end
    hess(end, end) = hess(end, end) + L^2 * err_term(3) * curv_dash_f;
    
    % hessian w.r.t curv
    for i = 2:num_params
        hess(end, i-1) = hess(end, i-1) + L^4 * err_term(4) * (i-1) * sf^(i-2);
        hess(i-1, end) = hess(i-1, end) + L^4 * err_term(4) * (i-1) * sf^(i-2);
    end
    hess(end, end) = hess(end, end) + L^4 * err_term(4) * curv_dash_dash_f;
    
    % additional terms
    hess = hess + grad_terms(1, :)' * grad_terms(1, :) + ...
        grad_terms(2, :)' * grad_terms(2, :) + ...
        L^2 * grad_terms(3, :)' * grad_terms(3, :) + ...
        L^4 * grad_terms(4, :)' * grad_terms(4, :);
    
%     hess = t * hess;
end