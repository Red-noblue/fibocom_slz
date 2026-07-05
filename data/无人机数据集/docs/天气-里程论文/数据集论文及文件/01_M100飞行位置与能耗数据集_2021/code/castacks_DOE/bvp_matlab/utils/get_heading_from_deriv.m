function [psi] = get_heading_from_deriv(theta_des, Vw, V)
    % check for low speeds
    if V < abs(Vw * sin(theta_des))
        % minimise component perpendicular to theta_des
        psi = get_heading_from_deriv(theta_des, Vw, abs(Vw * sin(theta_des)));
    else
        psi = wrapTo2Pi(acos(-(Vw*sin(theta_des))/V) - pi/2 + theta_des);
    end
end