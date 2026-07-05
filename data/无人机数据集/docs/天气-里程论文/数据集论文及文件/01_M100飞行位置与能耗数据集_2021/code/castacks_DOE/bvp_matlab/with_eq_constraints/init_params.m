function [q, dub_path] = init_params(X0, Xf, Xf_orig, num_poly_coeffs, v, vw_x, vw_y, params)
    % TODO - check for special cases (straight line, curv-currv-curv)

    L = 1; S = 2; R = 3;
    
    q = zeros(2*(num_poly_coeffs-1) + 3, 1);
    
    % get path from dubins
    [dub_path, l1, l2, l3, curv_type] = dubins_curve(X0(1:3), Xf(1:3), 1/params.max_kappa, 1, true);
    
    % check for direction of dubins curves
    r1 = .9; %0.5 + 0.5 *rand();
    r2 = .9; %0.5 + 0.5 *rand();
    head_change_1 = round(l1 * params.max_kappa * r1, 2);
    head_change_3 = round(l3 * params.max_kappa * r2, 2);
    if curv_type(1) == R
        head_change_1 = -head_change_1;
    end
    if curv_type(3) == R
        head_change_3 = -head_change_3;
    end
    
    % set up constraints for curv optimization 1
    if curv_type(2) == R
        constraints1.bv = [X0(4); -0.95*params.max_kappa];
    elseif curv_type(2) == L
        constraints1.bv = [X0(4); 0.95*params.max_kappa];
    else
        constraints1.bv = [X0(4); 0];
    end
    constraints1.bv_deriv = [0; 0];
    constraints1.bv_heading = [0; head_change_1];
    constraints1.curv_max = 0.95*params.max_kappa;
    constraints1.curv_rate = 0.95*params.max_kappa_rate;
    constraints1.curv_rate_rate = 0.95*params.max_kappa_rate;

    % set up constraints for curv optimization 2
    if curv_type(2) == R
        constraints3.bv = [-0.95*params.max_kappa; Xf(4)];
    elseif curv_type(2) == L
        constraints3.bv = [0.95*params.max_kappa; Xf(4)];
    else
        constraints3.bv = [0; Xf(4)];
    end
    constraints3.bv_deriv = [0; 0];
    constraints3.bv_heading = [0; head_change_3];
    constraints3.curv_max = 0.95*params.max_kappa;
    constraints3.curv_rate = 0.95*params.max_kappa_rate;
    constraints3.curv_rate_rate = 0.95*params.max_kappa_rate;

    % get curv poly1
    [c1, sf1, flag1] = get_curv_poly(params.num_curv_coeffs-1, constraints1, l1);

    % get curv poly3
    [c3, sf3, flag3] = get_curv_poly(params.num_curv_coeffs-1, constraints3, l3);
    
    % initialize sf2
%     if curv_type(2) == S
%         sf2 = .1 * l2;
%     else
%         sf2 = .5*l2;
%     end
    sf2 = max(0.9*l2+(l1+l3)-(sf1+sf3),1);
%     sf2 = 0.9*l2;
    if flag1 && flag3
        c1_scaled = fliplr(c1(1:end-1)) .* params.scales';
        c3_scaled = fliplr(c3(1:end-1)) .* params.scales';
        q = [c1_scaled'; c3_scaled'; round(sf1, 3); round(sf2, 3); round(sf3, 3)]; 
    end
    
%     load('init.mat');
%     q = q_init;
%     q(1:num_poly_coeffs-1) = q(1:num_poly_coeffs-1) .* params.scales;
%     q(num_poly_coeffs:end-3) = q(num_poly_coeffs:end-3) .* params.scales;
end