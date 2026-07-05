function [val] = comp_sns(psi_coeffs, sf, n)
    % computes \int_{0}^{s} s^{n} \sin(\psi(s)) ds
    
    fun = @(s) (s.^n) .* sin(wrapTo2Pi(polyval(psi_coeffs, s)));
    val = integral(fun, 0, sf);
end