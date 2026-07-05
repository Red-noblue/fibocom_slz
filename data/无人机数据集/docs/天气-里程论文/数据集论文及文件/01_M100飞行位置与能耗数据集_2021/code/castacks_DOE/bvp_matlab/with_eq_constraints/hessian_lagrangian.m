function [hess] = hessian_lagrangian(q, lambda, X0, vw_x, vw_y, v)
    num_constraints = 4;

    %% extract params
    num_params = length(q);
    sf = q(end);
    p = q(1:end-1);
    curv_coeffs = fliplr(p'); % follow matlab convention for polynomial coeffs
    psi_coeffs = polyint(curv_coeffs, X0(3));
    
    %% compute some end points
    psi_f = wrapTo2Pi(polyval(psi_coeffs, sf));
    curv_f = polyval(curv_coeffs, sf);
    curv_dash_f = polyval(polyder(curv_coeffs), sf);
    curv_dash_dash_f = polyval(polyder(polyder(curv_coeffs)), sf);
    
    %% compute hessian
    % hessian of cost function works out to zeros
    hess = zeros(num_params);
    
    % hessian w.r.t x
    for i = 1:num_params-1
        for j = 1:num_params-1
            hess(i, j) = hess(i, j) - lambda(1) * comp_cns(psi_coeffs, sf, i+j) / (j*i);
        end
        
        hess(end, i) = hess(end, i) - lambda(1) * (sf^i) * sin(psi_f) / i;
        hess(i, end) = hess(i, end) - lambda(1) * (sf^i) * sin(psi_f) / i;
    end
    hess(end, end) = hess(end, end) - lambda(1) * curv_f * sin(psi_f);

    % hessian w.r.t y
    for i = 1:num_params-1
        for j = 1:num_params-1
            hess(i, j) = hess(i, j) - lambda(2) * comp_sns(psi_coeffs, sf, i+j) / (j*i);
        end
        
        hess(end, i) = hess(end, i) + lambda(2) * (sf^i) * cos(psi_f) / i;
        hess(i, end) = hess(i, end) + lambda(2) * (sf^i) * cos(psi_f) / i;
    end
    hess(end, end) = hess(end, end) + lambda(2) * curv_f * cos(psi_f);
    
    % hessian w.r.t psi
    for i = 1:num_params-1
        hess(end, i) = hess(end, i) + lambda(3) * (sf^(i-1));
        hess(i, end) = hess(i, end) + lambda(3) * (sf^(i-1));
    end
    hess(end, end) = hess(end, end) + lambda(3) * curv_dash_f;
    
    % hessian w.r.t. curv
    for i = 1:num_params-1
        hess(end, i) = hess(end, i) + lambda(4) * (i-1) * sf^(i-2);
        hess(i, end) = hess(i, end) + lambda(4) * (i-1) * sf^(i-2);
    end
    hess(end, end) = hess(end, end) + lambda(4) * curv_dash_dash_f;
    
end