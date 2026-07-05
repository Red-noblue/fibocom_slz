function [psi_a, valid] = get_airframe_heading(v_a, psi_g, vw_x, vw_y)
    valid = true;
    wind_vect =[vw_x; vw_y];
    head_vect = [cos(psi_g); sin(psi_g)];

    wind_perp = wind_vect - (wind_vect' * head_vect) * head_vect;
    air_perp = -wind_perp;
    air_par_norm_sq = v_a^2 - air_perp' * air_perp;
    if(air_par_norm_sq < 0)
        psi_a = 0;
        valid = false;
        return;
    end

    air_par = sqrt(air_par_norm_sq) * head_vect;
    air_vect = air_perp + air_par;

    psi_a = wrapTo2Pi(atan2(air_vect(2), air_vect(1)));
end