function obj = obj_fn(q)
%     obj = 0.5 * sum(q(end-2:end))^2;
    obj = sum(q(end-2:end));
end