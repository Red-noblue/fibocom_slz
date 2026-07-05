clear all
% close all

data = readmatrix('data/large_data.csv');
data = sortrows(data,3);
% keyboard
% figure,
% for i=1:251
for i = 1640:1919
    q = data(i,12:22)';
    v = 5;
    vw_x = 0;
    vw_y = 0;
    num_poly_params = 4;
    q(1:num_poly_params) = q(1:num_poly_params);
    q(num_poly_params+1:2*num_poly_params) = q(num_poly_params+1:2*num_poly_params);
    X0 =   [0,0,0,0]';
    Xf = data(i,1:4);
    if Xf(1) <=45 || Xf(2) <=45
        continue
    end
    % extract params
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
    
    samples = linspace(0, sf, 100);
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
    %         figure, hold on;
    hold on
    plot(X0(1), X0(2), 'r*');
    plot(Xf(1), Xf(2), 'b*','MarkerSize',10,'LineWidth',20);
    plot(traj(:, 1), traj(:, 2), 'k-');
    drawnow
%     plot(perf.dub_path(:, 1), perf.dub_path(:, 2), 'g-');
    
end