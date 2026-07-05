function [coeffs, sf_final, flag] = get_curv_poly(degree, constraints, sf_init)
    sf_vals = sf_init:2:2*sf_init; % arbitrary?
    coeffs = [];
    sf_final = -1;    
    for sf = sf_vals
        [coeffs, flag] = get_curv_poly_with_sf(degree, constraints, sf);
        if flag
            sf_final = sf;
            return;
        end
    end
    
end