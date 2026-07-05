function [traj] = plot_stuff(q, X0, Xf, params, v, vw_x, vw_y, perf, can_plot)
    % scale poly coeffs
    num_poly_params = params.num_poly_params;
    q(1:num_poly_params) = q(1:num_poly_params) ./ params.scales;
    q(num_poly_params+1:2*num_poly_params) = q(num_poly_params+1:2*num_poly_params) ./ params.scales;
    
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
    curv_ds_coeffs = [polyder(c1); zeros(1, num_poly_params); polyder(c3)];
    psi_pp = mkpp(breaks, psi_coeffs);
    curv_pp = mkpp(breaks, curv_coeffs);
    curv_ds_pp = mkpp(breaks, curv_ds_coeffs);
    
    % define functions
    fun_x = @(s) cos(wrapTo2Pi(ppval(psi_pp, s)));
    fun_y = @(s) sin(wrapTo2Pi(ppval(psi_pp, s)));
    
    samples = linspace(0, sf, params.num_samples);
    traj = zeros(length(samples), 5);
    for i = 1:length(samples)
        s = samples(i);
        traj(i, 1) = integral(fun_x, 0, s) + s / v * vw_x;
        traj(i, 2) = integral(fun_y, 0, s) + s / v * vw_y;
        traj(i, 3) = ppval(psi_pp, s);
        traj(i, 4) = ppval(curv_pp, s);
        traj(i, 5) = ppval(curv_ds_pp, s);
    end
    
    % plot
    if can_plot
        figure, hold on;
        plot(X0(1), X0(2), 'r*');
        plot(Xf(1), Xf(2), 'b*');
        plot(traj(:, 1), traj(:, 2), 'k-');
        plot(perf.dub_path(:, 1), perf.dub_path(:, 2), 'g-');
    end
    % plot initial guess
    q = perf.q0;
    q(1:num_poly_params) = q(1:num_poly_params) ./ params.scales;
    q(num_poly_params+1:2*num_poly_params) = q(num_poly_params+1:2*num_poly_params) ./ params.scales;
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
    curv_ds_coeffs = [polyder(c1); zeros(1, num_poly_params); polyder(c3)];
    psi_pp = mkpp(breaks, psi_coeffs);
    curv_pp = mkpp(breaks, curv_coeffs);
    curv_ds_pp = mkpp(breaks, curv_ds_coeffs);

    % define functions
    fun_x = @(s) cos(wrapTo2Pi(ppval(psi_pp, s)));
    fun_y = @(s) sin(wrapTo2Pi(ppval(psi_pp, s)));
    
    samples = linspace(0, sf, params.num_samples);
    init_traj = zeros(length(samples), 5);
    for i = 1:length(samples)
        s = samples(i);
        init_traj(i, 1) = integral(fun_x, 0, s) + s / v * vw_x;
        init_traj(i, 2) = integral(fun_y, 0, s) + s / v * vw_y;
        init_traj(i, 3) = ppval(psi_pp, s);
        init_traj(i, 4) = ppval(curv_pp, s);
        init_traj(i, 5) = ppval(curv_ds_pp, s);
    end
        plot(init_traj(:, 1), init_traj(:, 2), 'm-');

    if can_plot
%         plot(init_traj(:, 1), init_traj(:, 2), 'm-');
        legend('start', 'goal', 'kite', 'initial guess');
    %     
    %     % plot constr violations
        figure, hold on
        plot(traj(:, 4), 'r-');
        plot(traj(:, 5), 'b-');
        legend('Curv', 'Curv rate');
        refline(0, params.max_kappa);
        refline(0, -params.max_kappa);
    end
end