function [grad] = get_gradient(q, num_poly_params, X0, Xf, L, v, vw_x, vw_y, lambda)
  
    % extract params
    sf1 = q(end-2);
    sf2 = q(end-1);
    sf3 = q(end);
    c1 = fliplr([X0(4); q(1:num_poly_params)]'); % follow matlab poly convention
    c2 = [zeros(1, num_poly_params), polyval(c1, sf1)]; % follow matlab poly convention
    c3 = fliplr([polyval(c2, sf2); q(num_poly_params+1:end-3)]'); % follow matlab poly convention
    psi1 = polyint(c1, X0(3));
    psi2 = polyint(c2, polyval(psi1, sf1));
    psi3 = polyint(c3, polyval(psi2, sf2));
    
    %% compute gradient
    err_term = terminal_error(q, num_poly_params, X0, Xf, 1, v, vw_x, vw_y);
    
    grad = err_term(1) * get_grad_x(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y) + ...
        err_term(2) * get_grad_y(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y) + ...
        L^2 * err_term(3) * get_grad_psi(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y) + ...
        L^4 * err_term(4) * get_grad_curv(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y) + ...
        lambda * get_grad_curv_cost(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y);
end

function [grad_x] = get_grad_x(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y)
    num_poly_params = length(c1) - 1;
    
    % set up functions and constants
    fun_sinns1 = @(s, pow) (s .^ pow) .* sin(polyval(psi1, s));
    fun_sinns2 = @(s, pow) (s .^ pow) .* sin(polyval(psi2, s));
    fun_sinns3 = @(s, pow) (s .^ pow) .* sin(polyval(psi3, s));
    c1_df = polyval(polyder(c1), sf1);
    c1_f = polyval(c1, sf1);
    psi1_f = polyval(psi1, sf1);
    
    % pre-compute some stuff
    dx2q1_1 = simpson_integration(fun_sinns2, 0, 101, 0, sf2);
    dx2q1_2 = simpson_integration(fun_sinns2, 1, 101, 0, sf2);
    dx3q1_1 = simpson_integration(fun_sinns3, 0, 101, 0, sf3);
    dx3q1_2 = simpson_integration(fun_sinns3, 1, 101, 0, sf3);
    
    % compute gradient
    grad_x = zeros(1, length(q));
    for i = 2:num_poly_params+1
        % for x1 w.r.t c1
        grad_x(i-1) = grad_x(i-1) - simpson_integration(fun_sinns1, i, 101, 0, sf1) / i;
        
        % for x2 w.r.t c1
        grad_x(i-1) = grad_x(i-1) + -(sf1^i * dx2q1_1 / i + sf1^(i-1) * dx2q1_2);
        
        % for x3 w.r.t c1
        grad_x(i-1) = grad_x(i-1) - (sf1^i/i + sf1^(i-1)*sf2) * dx3q1_1 - sf1^(i-1) * dx3q1_2;
        % for x3 w.r.t c3
        idx = num_poly_params + i - 1;
        grad_x(idx) = grad_x(idx) - simpson_integration(fun_sinns3, i, 101, 0, sf3) / i;
    end
        
    % for x1 w.r.t sf1
    grad_x(end-2) = grad_x(end-2) + cos(psi1_f);
    
    % for x2 w.r.t sf1
    grad_x(end-2) = grad_x(end-2) - c1_f * dx2q1_1 - c1_df * dx2q1_2;
    % for x2 w.r.t sf2
    grad_x(end-1) = grad_x(end-1) + cos(polyval(psi2, sf2));
    
    % for x3 w.r.t sf1
    grad_x(end-2) = grad_x(end-2) - (c1_f + c1_df * sf2) * dx3q1_1 - c1_df * dx3q1_2;
    % for x3 w.r.t sf2
    grad_x(end-1) = grad_x(end-1) - c1_f * dx3q1_1;
    % for x3 w.r.t sf3
    grad_x(end) = grad_x(end) + cos(polyval(psi3, sf3));
    
    % add in wind terms
    grad_x(end-2) = grad_x(end-2) + vw_x / v;
    grad_x(end-1) = grad_x(end-1) + vw_x / v;
    grad_x(end) = grad_x(end) + vw_x / v;
end

function [grad_y] = get_grad_y(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y)
    num_poly_params = length(c1) - 1;
    
    % set up functions and constants
    fun_cosns1 = @(s, pow) (s .^ pow) .* cos(polyval(psi1, s));
    fun_cosns2 = @(s, pow) (s .^ pow) .* cos(polyval(psi2, s));
    fun_cosns3 = @(s, pow) (s .^ pow) .* cos(polyval(psi3, s));
    c1_df = polyval(polyder(c1), sf1);
    c1_f = polyval(c1, sf1);
    psi1_f = polyval(psi1, sf1);
    
    % pre-compute some stuff
    dx2q1_1 = simpson_integration(fun_cosns2, 0, 101, 0, sf2);
    dx2q1_2 = simpson_integration(fun_cosns2, 1, 101, 0, sf2);
    dx3q1_1 = simpson_integration(fun_cosns3, 0, 101, 0, sf3);
    dx3q1_2 = simpson_integration(fun_cosns3, 1, 101, 0, sf3);
    
    % compute gradient
    grad_y = zeros(1, length(q));
    for i = 2:num_poly_params+1
        % for y1 w.r.t c1
        grad_y(i-1) = grad_y(i-1) + simpson_integration(fun_cosns1, i, 101, 0, sf1) / i;
        
        % for y2 w.r.t c1
        grad_y(i-1) = grad_y(i-1) + (sf1^i * dx2q1_1 / i + sf1^(i-1) * dx2q1_2);
        
        % for y3 w.r.t c1
        grad_y(i-1) = grad_y(i-1) + (sf1^i/i + sf1^(i-1)*sf2) * dx3q1_1 + sf1^(i-1) * dx3q1_2;
        % for y3 w.r.t c3
        idx = num_poly_params + i - 1;
        grad_y(idx) = grad_y(idx) + simpson_integration(fun_cosns3, i, 101, 0, sf3) / i;
    end
        
    % for y1 w.r.t sf1
    grad_y(end-2) = grad_y(end-2) + sin(psi1_f);
    
    % for y2 w.r.t sf1
    grad_y(end-2) = grad_y(end-2) + c1_f * dx2q1_1 + c1_df * dx2q1_2;
    % for y2 w.r.t sf2
    grad_y(end-1) = grad_y(end-1) + sin(polyval(psi2, sf2));
    
    % for y3 w.r.t sf1
    grad_y(end-2) = grad_y(end-2) + (c1_f + c1_df * sf2) * dx3q1_1 + c1_df * dx3q1_2;
    % for x3 w.r.t sf2
    grad_y(end-1) = grad_y(end-1) + c1_f * dx3q1_1;
    % for x3 w.r.t sf3
    grad_y(end) = grad_y(end) + sin(polyval(psi3, sf3));
    
    % add in wind terms
    grad_y(end-2) = grad_y(end-2) + vw_y / v;
    grad_y(end-1) = grad_y(end-1) + vw_y / v;
    grad_y(end) = grad_y(end) + vw_y / v;
end

function [grad_psi] = get_grad_psi(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y)
    num_poly_params = length(c1) - 1;

    c1_df = polyval(polyder(c1), sf1);
    c1_f = polyval(c1, sf1);
    
    % compute gradient
    grad_psi = zeros(1, length(q));
    for i = 2:num_poly_params+1
        % for psi w.r.t c1
        grad_psi(i-1) = grad_psi(i-1) + sf1^i/i + sf1^(i-1) * (sf2 + sf3);
        
        % for psi w.r.t c3
        idx = num_poly_params + i - 1;
        grad_psi(idx) = grad_psi(idx) + sf3^i / i;
    end
    
    % for psi w.r.t sf1
    grad_psi(end-2) = grad_psi(end-2) + c1_f + c1_df * (sf2 + sf3);
    
    % for psi w.r.t sf2
    grad_psi(end-1) = grad_psi(end-1) + c1_f;
    
    % for psi w.r.t sf3
    grad_psi(end) = grad_psi(end) + polyval(c3, sf3);
end

function [grad_curv] = get_grad_curv(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y)
    num_poly_params = length(c1) - 1;

    c1_df = polyval(polyder(c1), sf1);
    
    % compute gradient
    grad_curv = zeros(1, length(q));
    for i = 1:num_poly_params
        % for kappa w.r.t c1
        grad_curv(i) = grad_curv(i) + sf1^i;
        
        % for kappa w.r.t c3
        idx = num_poly_params + i;
        grad_curv(idx) = grad_curv(idx) + sf3^i;
    end
    
    % for kapps w.r.t sf1
    grad_curv(end-2) = grad_curv(end-2) + c1_df;
    
    % for kappa w.r.t sf2
    grad_curv(end-1) = grad_curv(end-1) + 0;
    
    % for kappa w.r.t sf3
    grad_curv(end) = grad_curv(end) + polyval(polyder(c3), sf3);
end

function [grad_curv_cost] = get_grad_curv_cost(q, c1, c2, c3, psi1, psi2, psi3, sf1, sf2, sf3, v, vw_x, vw_y)
    num_poly_params = length(c1) - 1;

    c1_df = polyval(polyder(c1), sf1);
    c1_f = polyval(c1, sf1);
    
    grad_curv_cost = zeros(1, length(q)); % only depends on q1
    for i = 1:num_poly_params
        grad_curv_cost(i) = grad_curv_cost(i) + sf1^i;
    end
    
    % w.r.t sf1
    grad_curv_cost(end-2) = grad_curv_cost(end-2) + c1_df;
    grad_curv_cost = grad_curv_cost * c1_f;
end