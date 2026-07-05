function [A, grad] = get_curv_constraint_terms(q, params, X0)
    num_poly_params = params.num_poly_params;
    
    % scale poly coeffs
    q(1:num_poly_params) = q(1:num_poly_params) ./ params.scales;
    q(num_poly_params+1:2*num_poly_params) = q(num_poly_params+1:2*num_poly_params) ./ params.scales;

    % extract params
    sf1 = q(end-2);
    sf2 = q(end-1);
    sf3 = q(end);
    c1 = fliplr([X0(4); q(1:num_poly_params)]'); % follow matlab poly convention
    c2 = [zeros(1, num_poly_params), polyval(c1, sf1)]; % follow matlab poly convention
    c3 = fliplr([polyval(c2, sf2); q(num_poly_params+1:end-3)]'); % follow matlab poly convention
    c1_f = polyval(c1, sf1);
    c1_df = polyval(polyder(c1), sf1);
    
    A = zeros(2*params.num_constraint_samples, 1);
    grad = zeros(2*params.num_constraint_samples, length(q));
    
    %% for c1
    s_vals = linspace(0, sf1, params.num_constraint_samples);
    for i = 1:params.num_constraint_samples
        s = s_vals(i);
        A(i) = polyval(c1, s)^2;
         
        % set up gradient
        c = polyval(c1, s);
        for j = 1:num_poly_params
            grad(i, j) = c * s^j;
        end
        grad(i, end-2) = c * polyval(polyder(c1), s);
    end
    
    %% for c3
    s_vals = linspace(0, sf3, params.num_constraint_samples);
    for i = 1:params.num_constraint_samples
        s = s_vals(i);
        idx = params.num_constraint_samples+i;
        A(idx) = polyval(c3, s)^2;
        
        % set up gradient
        c = polyval(c3, s);
        for j = 1:num_poly_params
            grad(idx, j) = c * sf1^j;
            
            grad(idx, num_poly_params+j) = c * s^j;
        end
        grad(idx, end-2) = c * polyval(polyder(c1), sf1);
        grad(idx, end) = c * polyval(polyder(c1), s);
    end

    A = 0.5 * (A - params.max_kappa^2);
    
end