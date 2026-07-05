function [q_init] = init_params(X0, Xf, num_coeffs, v, vw_x, vw_y, params)
%     q_init = zeros(num_coeffs, 1);
% 
%     d = sqrt((Xf(1) - X0(1))^2 + (Xf(2) - X0(2))^2);
%     del_psi = get_corr_heading_change(Xf(3), X0(3));
%     sf = d * (del_psi^2 / 5 + 1) + 0.4 * del_psi;
%     
%     % let's try and set the first 3 poly coeffs, and keep the others at
%     % zero
%     vals = [sf, sf^2; (sf^2)/2, (sf^3)/3] \ [Xf(4) - X0(4); Xf(3) - X0(4)*sf];
%     q_init(1) = vals(1);
%     q_init(2) = vals(2);
%     q_init(end) = sf;
    q_init = [fliplr([2.3313e-09,-3.9186e-07,1.6052e-05,0])'; 5];
%     q_init = [fliplr([0, 0, 0, 0])'; 5];

    % get path from dubins
    [path_dub, l1, l2, l3, curv_type] = dubins_curve(X0(1:3), Xf(1:3), 1/params.max_kappa, .1, true);
    
    % set up constraints for curv optimization 
    constraints1.bv = [X0(4); Xf(4)];
    constraints1.bv_deriv = [0; 0];
    constraints1.bv_heading = [0; Xf(3)];
    constraints1.curv_max = params.max_kappa;
    constraints1.curv_rate = params.max_kappa_rate;
    constraints1.curv_rate_rate = params.max_kappa_rate;
    
    % get curv poly1
    [c1, sf1, flag1] = get_curv_poly(params.num_curv_coeffs-1, constraints1, 15);
    if flag1
        q_init = [fliplr(c1(1:end-1))'; .8*sf1];
    end
end