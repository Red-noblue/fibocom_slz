function [traj] = get_curvpp_path(q, X0, Xf, params, v, vw_x, vw_y, perf)
    % extract params
    num_poly_params = params.num_poly_params;
    sf1 = q(end-2);
    sf2 = q(end-1);
    sf3 = q(end);
    sf = sf1 + sf2 + sf3;
    c1 = fliplr([X0(4); q(1:num_poly_params)]'); % follow matlab poly convention
    c2 = [zeros(1, num_poly_params), polyval(c1, sf1)]; % follow matlab poly convention
    c3 = fliplr([polyval(c2, sf2); q(num_poly_params+1:end-3)]'); % follow matlab poly convention
    psi1 = polyint(c1, X0(3));
    psi2 = polyint(c2, polyval(psi1, sf1));
    psi3 = polyint(c3, polyval(psi2, sf2));
    
    % make piecewise poly
    breaks = [0, sf1, sf1+sf2, sf1+sf2+sf3];
    psi_coeffs = [psi1; psi2; psi3];
    curv_coeffs = [c1; c2; c3];
    psi_pp = mkpp(breaks, psi_coeffs);
    curv_pp = mkpp(breaks, curv_coeffs);

    % define functions
    fun_x = @(s) cos(wrapTo2Pi(ppval(psi_pp, s)));
    fun_y = @(s) sin(wrapTo2Pi(ppval(psi_pp, s)));
    
    samples = linspace(0, sf, params.num_samples);
    traj = zeros(length(samples), 4);
    for i = 1:length(samples)
        s = samples(i);
        traj(i, 1) = integral(fun_x, 0, s) + s / v * vw_x;
        traj(i, 2) = integral(fun_y, 0, s) + s / v * vw_y;
        traj(i, 3) = ppval(psi_pp, s);
        traj(i, 4) = ppval(curv_pp, s);
    end
end