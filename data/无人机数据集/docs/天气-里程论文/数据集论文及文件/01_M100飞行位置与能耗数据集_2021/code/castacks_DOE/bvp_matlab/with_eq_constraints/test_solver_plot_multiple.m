clear; clc; close all
tic;
% define params
params.num_curv_coeffs = 5;
params.num_poly_params = params.num_curv_coeffs - 1;
params.num_constraints = 4;
params.num_samples = 100;
params.num_constraint_samples = 50;
params.max_kappa = 1/20;
params.max_kappa_rate = params.max_kappa;
params.bv_tol = [1e-1; 1e-1; 1e-3; 1e-4];
params.bv_tol_sincos = [1e-3; 1e-3; 1e-3; 1e-3; 1e-4];
params.curv1_tol = 1e-4;

% define scaling factors
params.scale_factor = 1;
params.scales = zeros(params.num_poly_params, 1);
for i = 1:params.num_poly_params
    params.scales(i) =  params.scale_factor^i;
end

% define speeds
v = 5;
vw_x = 0;
vw_y = 0;
bad_traj = [];
good_traj = [];
% define boundary values (x, y, psi, curv)
X0 = [0, 0, 0, 0];
init_x = [70, 80, pi/2, 0];

% possible_values = [, 100, 0, 0;
%                     90, 90, 0, 0;
%                     80, 80, 0, 0;
%                     70, 70, 0, 0];
possible_values = allcomb(68:1:72, 78:1:82, [pi/2], 0:0.1:0.5)';
% count = lenght(possible_values);
init_traj= [];
for Xf = possible_values
    %      Xf = possible_values(:,X)';
    %     %Xf = X';
    %     if (Xf(1) == 100 && Xf(2) > 35)
    %         continue;
    %     end
    % %     Xf = [70, 80, pi/2, 0];
    
    % convert groundframe heading into airframe heading
    Xf_orig = Xf;
    Xf(3) = get_airframe_heading(v, Xf(3), vw_x, vw_y);
    
    % define dynamics constraints
    dyn_constraints = [];
    
    % optimize!
    [q, perf] = solve_bvp_fmincon(X0, Xf, Xf_orig, v, vw_x, vw_y, params);
    toc
    % plot stuff
    
    tol = constr_violation(q, params.num_poly_params, X0, Xf, v, vw_x, vw_y, params);
    
    traj = plot_stuff(q, X0, Xf, params, v, vw_x, vw_y, perf);
    if abs(tol) <= [0.5, 0.5, 0.2, 0.2]'
        good_traj = [good_traj; traj];
    else
        bad_traj = [bad_traj; traj];
    end
    if Xf == init_x'
        init_traj = traj;
    end
    
end
hold on;
plot(good_traj(:,1), good_traj(:,2), 'go');
plot(bad_traj(:,1), bad_traj(:,2), 'ro');
plot(init_traj(:,1), init_traj(:,2), 'k');