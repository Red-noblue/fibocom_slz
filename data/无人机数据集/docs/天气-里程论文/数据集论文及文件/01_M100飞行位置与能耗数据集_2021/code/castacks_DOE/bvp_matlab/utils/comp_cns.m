function [val] = comp_cns(psi_coeffs, sf, n)
    % computes \int_{0}^{s} s^{n} \cos(\psi(s)) ds
    
    fun = @(s) (s.^n) .* cos(wrapTo2Pi(polyval(psi_coeffs, s)));
    val = integral(fun, 0, sf);
end