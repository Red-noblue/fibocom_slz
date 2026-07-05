function [A,b] = get_constraint(p0,sf)
p0 = p0';
ss = linspace(0,sf,100);
for i = 1:size(ss,2)
    s = ss(i);
    for j = size(p0,1):-1:1
        A(i,j) = s^j;
    end
end
A = fliplr(A);
A = [A zeros(100,1)];
A = [A;-A];
b = ones(2*size(ss,2),1)*(1/20);
end

