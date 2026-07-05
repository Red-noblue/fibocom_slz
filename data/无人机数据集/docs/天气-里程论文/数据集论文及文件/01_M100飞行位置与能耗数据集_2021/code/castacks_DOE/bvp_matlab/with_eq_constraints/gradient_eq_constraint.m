function [grad] = gradient_eq_constraint(q, X0, vw_x, vw_y, v)
    num_constraints = 4;

    %% extract params
    sf = q(end);
    p = q(1:end-1);
    curv_coeffs = fliplr(p'); % follow matlab convention for polynomial coeffs
    psi_coeffs = polyint(curv_coeffs, X0(3));
    
    %% compute gradient 
    grad = zeros(num_constraints, length(q));
    for i = 1:length(p)
        % grad for x
        grad(1, i) = -comp_sns(psi_coeffs, sf, i) / i;
        
        % grad for y
        grad(2, i) = comp_cns(psi_coeffs, sf, i) / i;
        
        % grad for psi
        grad(3, i) = (sf^i) / i;
        
        % grad for kappa
        grad(4, i) = sf ^ (i-1);
    end
    
    grad(1, end) = cos(wrapTo2Pi(polyval(psi_coeffs, sf))) + vw_x / v;
    grad(2, end) = sin(wrapTo2Pi(polyval(psi_coeffs, sf))) + vw_y / v;
    grad(3, end) = polyval(curv_coeffs, sf);
    grad(4, end) = polyval(polyder(curv_coeffs), sf);
end