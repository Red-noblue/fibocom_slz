function [curv_poly_coeffs, flag] = get_curv_poly_with_sf(degree, constraints, Sf)
    
    err_tol = 1e-2;
    num_samples = 100;
    flag = false;
    
    %% Set up LHS
    % boundary values
    C_bv = [];
    if ~isempty(constraints.bv)
        C_bv = zeros(2, degree+1);
        for i = degree:-1:0
            C_bv(1, degree-i+1) = 0 ^ i;
            C_bv(2, degree-i+1) = Sf ^ i;
        end
    end

    % boundary derivative values
    C_bv_deriv = [];
    if ~isempty(constraints.bv_deriv)
        C_bv_deriv = zeros(2, degree+1);
        for i = degree:-1:1
            C_bv_deriv(1, degree-i+1) = i * 0 ^ (i-1);
            C_bv_deriv(2, degree-i+1) = i * Sf ^ (i-1);
        end
    end
    
    C_bv_heading = [];
    if ~isempty(constraints.bv_heading)
        C_bv_heading = zeros(2, degree+1);
        for i = degree:-1:0
            C_bv_heading(1, degree-i+1) = 0;
            C_bv_heading(2, degree-i+1) = Sf^(i+1) / (i+1);
        end
    end

    C = [C_bv; C_bv_deriv; C_bv_heading];

    %% Set up RHS
    d = [constraints.bv; constraints.bv_deriv; constraints.bv_heading];

    %% Set up box constraints
    lb = -0.01 * ones(degree+1, 1);
%     lb(1) = -0.001;
    ub = 0.01 * ones(degree+1, 1);
%     ub(1) = 0.001;

    %% Set up inequality constraints
    samples = transpose(linspace(0, Sf, num_samples));

    % Curvature constraint
    A_curv = [];
    for i = degree:-1:0
        A_curv = [A_curv [samples.^i; -samples.^i]];
    end
    b_curv = zeros(size(A_curv, 1), 1) + constraints.curv_max;

    % Curvature rate constraint
    A_deriv = [];
    for i = degree:-1:1
        A_deriv = [A_deriv [i * samples.^(i-1); -i * samples.^(i-1)]]; 
    end
    A_deriv = [A_deriv zeros(2*length(samples), 1)];
%         A_deriv = A_deriv / (samples(2) - samples(1));
    b_deriv = zeros(size(A_deriv, 1), 1) + constraints.curv_rate;

    % Curvature rate rate constraint
    A_dderiv = []; b_dderiv = [];
    if ~isempty(constraints.curv_rate_rate)
        for i = degree:-1:2
            A_dderiv = [A_dderiv [i * (i-1) * samples.^(i-2); ...
                -i * (i-1) * samples.^(i-2)]]; 
        end
        A_dderiv = [A_dderiv zeros(2*length(samples), 2)];
        b_dderiv = zeros(size(A_dderiv, 1), 1) + constraints.curv_rate_rate;
    end

    A = [A_curv; A_deriv; A_dderiv];
    b = [b_curv; b_deriv; b_dderiv];

    options = optimset('MaxIter', 5500, 'Algorithm', 'interior-point', 'display', 'off');
    [curv_poly_coeffs, resnorm,residual,exitflag,output,lambda] = lsqlin(C, d, A, b, [], [], lb, ub, [], options);
    curv_poly_coeffs = curv_poly_coeffs';
    %% Check if we've found a satisfactory solution
%     C*curv_poly_coeffs'
    
    if norm(abs(residual)) < err_tol && output.constrviolation < eps
        flag = true;
%             curv_poly_coeffs = (C \ d)';
        return;
    end
    
%     curv_poly_coeffs = (C \ d)';
end