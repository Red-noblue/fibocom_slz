#ifndef KITE_BVP_SOLVER_INCLUDE_KITE_UTILS_H
#define KITE_BVP_SOLVER_INCLUDE_KITE_UTILS_H

#include <Eigen/Dense>
#include "math_utils/math_utils.h"


namespace ca {
namespace kite_bvp_solver {  

inline double CompCosNPsi(double psi, double mult) {
  return mult * std::cos(psi);
}

inline double CompSinNPsi(double psi, double mult) {
  return mult * std::sin(psi);
}

inline double GetAirframeHeading(double v_a, double psi_g, double vw_x, double vw_y, bool &valid) {
  valid = true;

  // we compute air-frame heading by assuming zero side-slip
  Eigen::Vector2d wind_vect, head_vect, air_perp, air_vect;
  wind_vect << vw_x, vw_y;
  head_vect << std::cos(psi_g), std::sin(psi_g);
  air_perp = -(wind_vect - wind_vect.dot(head_vect) * head_vect);
  double air_par_norm_sq = v_a * v_a - air_perp.squaredNorm();
  if(air_par_norm_sq < 0) {
    // sanity check
    valid = false;
    return 0;
  }

  air_vect = air_perp + std::sqrt(air_par_norm_sq) * head_vect;
  return ca::math_utils::angular_math::WrapTo2Pi(std::atan2(air_vect(1), air_vect(0)));
}

inline double RoundToTwoPlaces(double val) {
  return std::round(val * 100.) / 100.;
}

  
}
}

#endif