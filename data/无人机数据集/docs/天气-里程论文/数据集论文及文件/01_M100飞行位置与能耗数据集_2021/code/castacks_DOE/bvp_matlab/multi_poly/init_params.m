function [q, dub_path] = init_params(X0, Xf, num_poly_coeffs, v, vw_x, vw_y, params)
    % TODO - check for special cases (straight line, curv-currv-curv)

    L = 1; S = 2; R = 3;
    
    q = zeros(2*(num_poly_coeffs-1) + 3, 1);
    
    % get path from dubins
    [dub_path, l1, l2, l3, curv_type] = dubins_curve(X0(1:3), Xf(1:3), 1/params.max_kappa, 1, true);
    
    % check for direction of dubins curves
    head_change_1 = l1 * params.max_kappa; 
    head_change_3 = l3 * params.max_kappa;
    if curv_type(1) == R
        head_change_1 = -head_change_1;
    end
    if curv_type(3) == R
        head_change_3 = -head_change_3;
    end
    
    % set up constraints for curv optimization 1
    constraints1.bv = [X0(4); Xf(4)];
    constraints1.bv_deriv = [0; 0];
    constraints1.bv_heading = [0; head_change_1];
    constraints1.curv_max = params.max_kappa;
    constraints1.curv_rate = params.max_kappa_rate;
    constraints1.curv_rate_rate = params.max_kappa_rate;

    % set up constraints for curv optimization 2
    constraints3.bv = [X0(4); Xf(4)];
    constraints3.bv_deriv = [0; 0];
    constraints3.bv_heading = [0; head_change_3];
    constraints3.curv_max = params.max_kappa;
    constraints3.curv_rate = params.max_kappa_rate;
    constraints3.curv_rate_rate = params.max_kappa_rate;

    % get curv poly1
    [c1, sf1, flag1] = get_curv_poly(params.num_curv_coeffs-1, constraints1, l1);

    % get curv poly3
    [c3, sf3, flag3] = get_curv_poly(params.num_curv_coeffs-1, constraints3, l3);
    sf2 = l2;
    
    if flag1 && flag3
        q = [fliplr(c1(1:end-1))'; fliplr(c3(1:end-1))'; sf1; sf2; sf3]; 
    end
end