syms sf1 sf2 sf3 b1 c1 d1 e1 b3 c3 d3 e3 s

kappa1 = b1 * s + c1 * s^2 + d1 * s^3 + e1 * s^4;
kappa1_f = b1 * sf1 + c1 * sf1^2 + d1 * sf1^3 + e1 * sf1^4;
kappa1_df = diff(kappa1_f, sf1);
psi1 = int(kappa1, s);
psi1_f = int(kappa1, s, 0, sf1);
x1f = int(cos(psi1), s, 0, sf1);
y1f = int(sin(psi1), s, 0, sf1);

kappa2 = kappa1_f;
psi2 = psi1_f + int(kappa2, s);
psi2_f = psi1_f + int(kappa2, s, 0, sf2);
x2f = int(cos(psi2), s, 0, sf2);
y2f = int(sin(psi2), s, 0, sf2);

kappa3 = kappa2 + b3 * s + c3 * s^2 + d3 * s^3 + e3 * s^4;
k3_f = b3 * sf3 + c3 * sf3^2 + d3 * sf3^3 + e3 * sf3^4;
psi3 = psi2_f + int(kappa3, s);
psi3_f = psi2_f + int(kappa3, s, 0, sf3);
x3f = int(cos(psi3), s, 0, sf3);
y3f = int(sin(psi3), s, 0, sf3);

dx = int(-(sf1^3/3 + sf1^2*s) * sin(psi2), s, 0, sf2);