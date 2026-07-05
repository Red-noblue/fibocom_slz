function [] = plot_stuff(X0, Xf, curv_coeffs, sf, params, v, vw_x, vw_y, perf)
 
    psi_coeffs = polyint(curv_coeffs, X0(3));
    
    %% generate traj
    samples = linspace(0, sf, params.num_samples);
    traj = zeros(length(samples), 4);
    for i = 1:length(samples)
        s = samples(i);
        traj(i, 1) = comp_cns(psi_coeffs, s, 0) + s / v * vw_x;
        traj(i, 2) = comp_sns(psi_coeffs, s, 0) + s / v * vw_y;
        traj(i, 3) = polyval(psi_coeffs, s);
        traj(i, 4) = polyval(curv_coeffs, s);
    end
    
    %% plot stuff
    figure, hold on
    plot(X0(1), X0(2), 'r*');
    plot(Xf(1), Xf(2), 'b*');
    plot(traj(:, 1), traj(:, 2), 'k-');
end