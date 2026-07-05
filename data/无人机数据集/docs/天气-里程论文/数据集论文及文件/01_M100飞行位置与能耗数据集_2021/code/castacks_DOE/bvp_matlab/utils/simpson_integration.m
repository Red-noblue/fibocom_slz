function [val] = simpson_integration(fun, fun_params, n, low_lim, upper_lim)
    % generate samples
    samples = linspace(low_lim, upper_lim, n);
    
    % integrate!
    weights = [1, 4, repmat([2, 4], 1, (n-3)/2), 1];
    fn_vals = fun(samples, fun_params);
    val = (samples(2) - samples(1)) * weights * fn_vals' / 3; 
%     val = round(val, 2);
end