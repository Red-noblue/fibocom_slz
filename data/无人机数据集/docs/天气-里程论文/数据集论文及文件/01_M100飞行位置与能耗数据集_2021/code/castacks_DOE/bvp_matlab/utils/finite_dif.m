function [grad] = finite_dif(fun, q)
    grad = zeros(1, length(q));
    
    h = sqrt(eps);
    h_sf = sqrt(eps);
    for i = 1:length(q)
        q_temp = q;
        if i == length(q)
            q_temp(i) = q_temp(i) + h_sf;
        else
            q_temp(i) = q_temp(i) + h;
        end
        grad(i) = (fun(q_temp) - fun(q)) / h;
    end
end