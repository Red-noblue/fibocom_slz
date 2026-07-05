#ifndef KITE_BVP_SOLVER_INCLUDE_KITE_BVP_DEFS_H
#define KITE_BVP_SOLVER_INCLUDE_KITE_BVP_DEFS_H

#include "polynomials/polynomials.h"
#include <Eigen/Dense>

namespace ca {
namespace kite_bvp_solver {

/************************** Type definitions **********************************/
  struct Params {
  int num_constraint_samples;
  int num_simpson_samples;
  double bv_tol[5];
  double curv1_tol;
  double precision;
  double constraint_tol;
};

struct Constraints {
  double max_curv;
  double max_curv_rate;
};

struct BVProblem {
  // boundary values
  std::vector<double> X0 = std::vector<double>(4);
  std::vector<double> Xf = std::vector<double>(4);

  // speeds
  double v, vw_x, vw_y;
};

template <class T, size_t degree_> struct OptData {
  // problem, params and constraints
 // nlopt::opt *opt;
  BVProblem problem;
  Params params;
  Constraints constraints;
  int count;
  double p_prv[degree_*2+3];
  // curvature and heading polys
  Polynomial<double, degree_> c1;
  Polynomial<double, degree_> c2;
  Polynomial<double, degree_> c3;
  Polynomial<double, degree_+1> psi1;
  Polynomial<double, degree_+1> psi2;
  Polynomial<double, degree_+1> psi3;
  Polynomial<double, degree_-1> c1_d;
  Polynomial<double, degree_-1> c3_d;
  double sf1, sf2, sf3;
  double ds1, ds2, ds3; // step-size for sf1, sf2, sf3

  // Ax <= b. cached linear inequality terms to check for curv and curv-rate violations
  Eigen::MatrixXd A;
  Eigen::VectorXd b; 

  // cached values of integrals computed using simpson's method
  Eigen::VectorXd c1_cos_cache, c2_cos_cache, c3_cos_cache;
  Eigen::VectorXd c1_sin_cache, c2_sin_cache, c3_sin_cache;
  Eigen::VectorXd simpson_wts;

  // cached values of some pow terms
  Eigen::VectorXd sf1_pow, sf3_pow;

  // other cached values
  double psi1_f, c1_f, c1_df, psi2_f, psi3_f;
  
  // data structure for terminal error
  std::vector<double> terminal_error = std::vector<double>(5);
};

} // kite_bvp_solver
} // ca

#endif