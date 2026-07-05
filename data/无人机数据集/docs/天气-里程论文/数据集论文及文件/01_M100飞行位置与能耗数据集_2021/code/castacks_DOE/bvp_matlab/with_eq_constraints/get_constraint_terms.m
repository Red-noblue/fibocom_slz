function [A, b] = get_constraint_terms(q0, params)
    sf1 = q0(end-2);
    sf3 = q0(end);
    sf = max(sf1, sf3) * 2;
    s_vals = linspace(0, sf, params.num_constraint_samples);
    
    num_params = length(q0);
    
    % for C1
    A_curv_1 = zeros(2*length(s_vals), num_params); 
    for i = 1:length(s_vals)
        s = s_vals(i);
        for j = 1:params.num_poly_params
            A_curv_1(i, j) = s^j / params.scales(j);
            A_curv_1(i+params.num_constraint_samples, j) = -s^j / params.scales(j);
        end
    end
    
    % for C3
    A_curv_3 = zeros(2*length(s_vals), num_params); 
    for i = 1:length(s_vals)
        s = s_vals(i);
        for j = 1:params.num_poly_params
            A_curv_3(i, j+params.num_poly_params) = s^j / params.scales(j);
            A_curv_3(i+params.num_constraint_samples, j+params.num_poly_params) = -s^j / params.scales(j);
        end
    end
    
    % for C1
    A_curv_rate_1 = zeros(2*length(s_vals), num_params); 
    for i = 1:length(s_vals)
        s = s_vals(i);
        for j = 1:params.num_poly_params
            A_curv_rate_1(i, j) = j * s^(j-1) / params.scales(j);
            A_curv_rate_1(i+params.num_constraint_samples, j) = -j * s^(j-1) / params.scales(j);
        end
    end
    
    % for C3
    A_curv_rate_3 = zeros(2*length(s_vals), num_params); 
    for i = 1:length(s_vals)
        s = s_vals(i);
        for j = 1:params.num_poly_params
            A_curv_rate_3(i, j+params.num_poly_params) = j * s^(j-1) / params.scales(j);
            A_curv_rate_3(i+params.num_constraint_samples, j+params.num_poly_params) = ...
                -j * s^(j-1) / params.scales(j);
        end
    end
    
    
    A = [A_curv_1; A_curv_3; A_curv_rate_1; A_curv_rate_3];
    b = [zeros(4*length(s_vals), 1) + params.max_kappa; ...
        zeros(4*length(s_vals), 1) + params.max_kappa_rate];
end