function [head_change] = get_corr_heading_change(heading1, heading2)
% assuming heading1 and heading2 are in [0, 2pi]
% Counter-clockwise rotation -> +ve
    head_change = abs(heading2 - heading1);
    if head_change > pi
        head_change = 2*pi - abs(head_change);
    end
    
    temp = cross([cos(heading1) sin(heading1) 0], [cos(heading2) sin(heading2) 0]);
    head_change = head_change * sign(temp(3));
end