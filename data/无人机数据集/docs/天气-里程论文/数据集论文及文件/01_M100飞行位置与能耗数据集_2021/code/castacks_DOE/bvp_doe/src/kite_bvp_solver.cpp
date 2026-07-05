#include "kite_bvp_solver/kite_bvp_solver.h"
#include <iostream>
#include <nlopt.hpp>
#include "math_utils/math_utils.h"

namespace ca {
namespace kite_bvp_solver {

template <class T, size_t degree_>
KiteBVPSolver<T, degree_>::KiteBVPSolver() {}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
Initialize(Params &params, Constraints &constraints) {
  params_ = params;
  constraints_ = constraints;
  num_params_ = 2*degree_ + 3;
  opt_data_ = new OptData<double, degree_>;
  init_guess_ = std::vector<double>(num_params_);
  lb_ = std::vector<double>(num_params_);
  ub_ = std::vector<double>(num_params_);
  tol_ = std::vector<double>(6 + params.num_constraint_samples*4, params.constraint_tol);
  InitOptData(opt_data_);
}

template <class T, size_t degree_>
bool KiteBVPSolver<T, degree_>::
SolveBVP(BVProblem &problem, double &min_cost, double &step_size, 
  Eigen::MatrixXd &path) {
  // modify end-heading to deal with wind
  bool valid;
  problem.Xf(2) = GetAirframeHeading(problem.v, problem.Xf(2), problem.vw_x, 
    problem.vw_y, valid);
  if(!valid) {
    // airspeed is too low compared to wind speed
    return valid;
  }

  problem_ = problem;
  opt_data_->problem = problem;

  // Get initial guess
  GetInitGuess();

  // generate upper and lower bounds
  for(int i = 0; i < num_params_; ++i) {
    if(i <= num_params_-3) {
      // poly coeffs
      lb_[i] = -1e-2;
      ub_[i] = 1e-2;
    }
    else {
      // arc lengths
      lb_[i] = 0;
      ub_[i] = 2 * init_guess_[i];
    }
  }

  // update optimization data
  UpdateOptData(opt_data_, 
    std::max(init_guess_[num_params_-3], init_guess_[num_params_-1]) * 2);

  // set up nlopt object
  nlopt::opt opt(nlopt::LD_SLSQP, num_params_);

  // set bounds
  opt.set_lower_bounds(lb_);
  opt.set_upper_bounds(ub_);

  // Set minimization objective
  opt.set_min_objective(ObjFn, (void *) opt_data_);

  // set constraint function
  opt.add_inequality_mconstraint(ConstraintFn, (void *) opt_data_, tol_);

  // set stopping criteria
  opt.set_xtol_rel(1e-10);
  opt.set_maxtime(10);

  // optimize
  try {
    nlopt::result result = opt.optimize(init_guess_, min_cost);
    if (result == nlopt::SUCCESS || result == nlopt::FTOL_REACHED || result == nlopt::XTOL_REACHED
        || result == nlopt::MAXTIME_REACHED) {
      GetPath(path, valid, step_size);
      return valid;
    } else {
      return false;
    }
  } catch (...) {
    return false;
  }
}

template <class T, size_t degree_>
double KiteBVPSolver<T, degree_>::
ObjFn(unsigned n, const double* x, double* grad, void* f_data) {
  // set gradient if it's not null
  if(grad != NULL) {
    grad[n-1] = 1;
    grad[n-2] = 1;
    grad[n-3] = 1;

    for(int i = 0; i <= n-4; ++i) {
      grad[i] = 0;
    }
  }

  return x[n-1] + x[n-2] + x[n-3];
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
ConstraintFn(unsigned m, double* result, unsigned n, const double* p, double* grad, void* f_data) {
  // unpack opt data
  OptData<double, degree_> *opt_data = static_cast<OptData<double, degree_>*>(f_data);
  Params params = opt_data->params;
  Constraints constr = opt_data->constraints;
  BVProblem problem = opt_data->problem;

  // unpack param vector and create polynomials
  UnpackParams(p, n, opt_data);

  // Pre-compute and cache a bunch of terms that we'll keep using
  PreCompute(opt_data);

  // Populate the constraint violation
  GetTerminalError(opt_data);
  result[0] = 0.5 * std::pow(opt_data->terminal_error(0), 2) - opt_data->params.bv_tol[0];
  result[1] = 0.5 * std::pow(opt_data->terminal_error(1), 2) - opt_data->params.bv_tol[1];
  result[2] = 0.5 * std::pow(opt_data->terminal_error(2), 2) - opt_data->params.bv_tol[2];
  result[3] = 0.5 * std::pow(opt_data->terminal_error(3), 2) - opt_data->params.bv_tol[3];
  result[4] = 0.5 * std::pow(opt_data->terminal_error(4), 2) - opt_data->params.bv_tol[4];
  result[5] = 0.5 * std::pow(opt_data->c1_df, 2) - opt_data->params.curv1_tol;

  if(grad == NULL) {
    // nothing more to do here
    return;
  }

  // compute gradients. This is an m*n array, where the gradient for constraint_1 is 
  // stored in the first n blocks, and so on.

  // zero out gradients first
  memset(grad, 0, m*n*sizeof(double)); // TODO - check

  // compute gradients for each of the boundary value inequality constraints
  GradX(grad, n, opt_data);
  GradY(grad, n, opt_data);
  GradPsi(grad, n, opt_data);
  GradCurv(grad, n, opt_data);

  // compute gradient for c1_df
  GradCurvDeriv(grad, n, opt_data);

  // compute constr violations and gradients for curvatures
  CurvConstraintFn(result, grad, n, opt_data);
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GetTerminalError(OptData<double, degree_> *opt_data) {
  // get terminal X, Y, psi and curv vals
  double sf = opt_data->sf1 + opt_data->sf2 + opt_data->sf3;
  double x_f = opt_data->c1_cos_cache(0) + opt_data->c2_cos_cache(0) + opt_data->c3_cos_cache(0) + 
    sf * opt_data->problem.vw_x / opt_data->problem.v;
  double y_f = opt_data->c1_sin_cache(0) + opt_data->c2_sin_cache(0) + opt_data->c3_sin_cache(0) + 
    sf * opt_data->problem.vw_y / opt_data->problem.v;
  double psi_f = opt_data->psi3.Evaluate(opt_data->sf3);
  double curv_f = opt_data->c3.Evaluate(opt_data->sf3);
  
  opt_data->terminal_error(0) = x_f - opt_data->problem.Xf(0);
  opt_data->terminal_error(1) = y_f - opt_data->problem.Xf(1);
  opt_data->terminal_error(2) = std::cos(psi_f) - std::cos(opt_data->problem.Xf(2));
  opt_data->terminal_error(3) = std::sin(psi_f) - std::sin(opt_data->problem.Xf(2));
  opt_data->terminal_error(4) = curv_f - opt_data->problem.Xf(3);
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GetInitGuess() {

}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GetPath(Eigen::MatrixXd &path, bool &valid, double step_size) {
  // unpack params
  UnpackParams(*init_guess_.data(), num_params_, opt_data_);
  double sf = opt_data_->sf1 + opt_data_->sf2 + opt_data_->sf3;
  unsigned num_path = int(sf / step_size) + 1;
  path.resize(num_path, 4);
  std::vector<Polynomial<double, degree_>> curv_polys = {opt_data_->c1, opt_data_->c2, opt_data_->c3};
  std::vector<Polynomial<double, degree_+1>> psi_polys = {opt_data_->psi1, opt_data_->psi2, opt_data_->psi3};
  std::vector<double> breaks = {0, opt_data_->sf1, opt_data_->sf1+opt_data_->sf2, sf};

  // evaluate solution to get path
  double prev_x(0), prev_y(0), s(0), curv, psi, x, y, cos_psi, sin_psi, prev_cos, prev_sin;
  int curr_id(0), path_id(1);
  path.row(0) = problem_.X0;
  prev_cos = std::cos(psi_polys[curr_id].Evaluate(0));
  prev_sin = std::sin(psi_polys[curr_id].Evaluate(0));
  while(s <= sf) {
    // check which poly we should evaluate
    if(s > breaks[curr_id+1]) {
      // move on to the next poly
      ++curr_id;
    }

    curv = curv_polys[curr_id].Evaluate(s - breaks[curr_id]);
    psi = ca::math_utils::angular_math::WrapTo2Pi(problem_.X0(2) + 
      psi_polys.Evaluate(s - breaks[curr_id]));
    cos_psi = std::cos(psi);
    sin_psi = std::sin(psi);

    // perform integrations using the trapezoidal rule (accurate enough?)
    x = path(path_id-1, 0) + step_size * (cos_psi + prev_cos) / 2 + problem_.vw_x * s / problem_.v;
    y = path(path_id-1, 1) + step_size * (sin_psi + prev_sin) / 2 + problem_.vw_y * s / problem_.v;
    path(path_id, 0) = x;
    path(path_id, 1) = y; 
    path(path_id, 2) = psi;
    path(path_id, 3) = curv;
    ++path_id;
    prev_cos = cos_psi;
    prev_sin = sin_psi;

    s += step_size;
  }

  // check for bv constraint sastisfaction
  --path_id;
  valid = true;
  if(0.5 * std::pow(path(path_id, 0) - problem_.Xf[0], 2 ) > params_.bv_tol[0]) {
    valid = false;
  }
  if(0.5 * std::pow(path(path_id, 1) - problem_.Xf[1], 2 ) > params_.bv_tol[1]) {
    valid = false;
  }
  if(0.5 * std::pow(std::cos(path(path_id, 2)) - std::cos(problem_.Xf[2]), 2 ) > params_.bv_tol[2]) {
    valid = false;
  }
  if(0.5 * std::pow(std::sin(path(path_id, 2)) - std::sin(problem_.Xf[2]), 2 ) > params_.bv_tol[3]) {
    valid = false;
  }
  if(0.5 * std::pow(path(path_id, 3) - problem_.Xf[3], 2 ) > params_.bv_tol[4]) {
    valid = false;
  }
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
InitOptData(OptData<double, degree_> *opt_data) {
  opt_data->params = params_;
  opt_data->constraints = constraints_;

  // fill up s_vals
  opt_data->s_vals = Eigen::VectorXd::Constant(params_.num_constraint_samples, 0);

  // initialize caches
  opt_data->c1_cos_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->c2_cos_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->c3_cos_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->c1_sin_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->c2_sin_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->c3_sin_cache = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->sf1_pow = Eigen::VectorXd::Constant(degree_+1, 0);
  opt_data->sf3_pow = Eigen::VectorXd::Constant(degree_+1, 0);

  // set simpson weights
  opt_data->simpson_wts = Eigen::VectorXd::Constant(params_.num_simpson_samples, 0);
  opt_data->simpson_wts(0) = 1;
  opt_data->simpson_wts(1) = 4;
  opt_data->simpson_wts(params_.num_simpson_samples-1) = 1;
  for(int i = 2; i <= params_.num_simpson_samples-2; ++i) {
    opt_data->simpson_wts(i) = (i % 2 == 0) ? 2 : 4;
  }
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
UpdateOptData(OptData<double, degree_> *opt_data, double s_max) {
  opt_data->s_vals << Eigen::VectorXd::LinSpaced(
    Eigen::Sequential, params_.num_constraint_samples, 0, s_max);  
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
UnpackParams(double *p, unsigned int n, OptData<double, degree_> *opt_data) {
  int num_poly_params = degree_;
  BVProblem problem = opt_data->problem;

  // extract distances
  opt_data->sf1 = p[n-3];
  opt_data->sf2 = p[n-2];
  opt_data->sf3 = p[n-1];

  // create curvature polys
  opt_data->c1[0] = problem.X0(3); // set to initial curvature
  for(int i = 0; i < num_poly_params; ++i) {
    opt_data->c1[i+1] = p[i];
    opt_data->c3[i+1] = p[i+num_poly_params];
  }
  opt_data->c2[0] = opt_data->c1.Evaluate(opt_data->sf1);
  opt_data->c3[0] = opt_data->c2.Evaluate(opt_data->sf2);
;
  // create heading polys
  opt_data->psi1.SetToIntegral(opt_data->c1, problem.X0(2));
  opt_data->psi2.SetToIntegral(opt_data->c2, opt_data->psi1.Evaluate(opt_data->sf1));
  opt_data->psi3.SetToIntegral(opt_data->c3, opt_data->psi2.Evaluate(opt_data->sf12));

  // create derivative polys
  opt_data->c1_d.SetToDerivative(opt_data->c1);
  opt_data->c3_d.SetToDerivative(opt_data->c3);
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
PreCompute(OptData<double, degree_> *opt_data) {
  double s1, s2, s3, wt;
  double c1_cos, c2_cos, c3_cos, c1_sin, c2_sin, c3_sin;

  // zero out the integral caches
  opt_data->c1_cos_cache.setZero();
  opt_data->c2_cos_cache.setZero();
  opt_data->c3_cos_cache.setZero();
  opt_data->c1_sin_cache.setZero();
  opt_data->c2_sin_cache.setZero();
  opt_data->c3_sin_cache.setZero();

  // generate step-sizes for sf1, sf2 and sf3
  opt_data->ds1 = opt_data->sf1 / (opt_data->params.num_simpson_samples-1);
  opt_data->ds2 = opt_data->sf2 / (opt_data->params.num_simpson_samples-1);
  opt_data->ds3 = opt_data->sf3 / (opt_data->params.num_simpson_samples-1);

  // generate and cache powers of sf1, sf2 and sf3
  opt_data->sf1_pow(0) = 1;
  opt_data->sf3_pow(0) = 1;
  for(int i = 1; i <= degree_+1; ++i) {
    opt_data->sf1_pow(i) = std::pow(opt_data->sf1, i);
    opt_data->sf3_pow(i) = std::pow(opt_data->sf3, i);
  }

  // generate and cache integral terms
  for(int i = 0; i < opt_data->params.num_simpson_samples; ++i) {
    s1 = i * opt_data->ds1;
    s2 = i * opt_data->ds2;
    s3 = i * opt_data->ds3;
    wt = opt_data->simpson_wts(i);

    // generate sines and cosines multiplied by the simpson weight
    c1_cos = std::cos(opt_data->psi1.Evaluate(s1)) * wt;
    c2_cos = std::cos(opt_data->psi2.Evaluate(s2)) * wt;
    c3_cos = std::cos(opt_data->psi3.Evaluate(s3)) * wt;
    c1_sin = std::sin(opt_data->psi1.Evaluate(s1)) * wt;
    c2_sin = std::sin(opt_data->psi2.Evaluate(s2)) * wt;
    c3_sin = std::sin(opt_data->psi3.Evaluate(s3)) * wt;
    opt_data->c1_cos_cache(0) += c1_cos;
    opt_data->c2_cos_cache(0) += c2_cos;
    opt_data->c3_cos_cache(0) += c3_cos;
    opt_data->c1_sin_cache(0) += c1_sin;
    opt_data->c2_sin_cache(0) += c2_sin;
    opt_data->c3_sin_cache(0) += c3_sin;

    // generate s^n * cos etc. terms
    opt_data->c2_cos_cache(1) += s2 * c2_cos;
    opt_data->c2_sin_cache(1) += s2 * c2_sin;
    for(int j = 1; j <= degree_+1; ++j) {
      opt_data->c1_cos_cache(j) += std::pow(s1, j) * c1_cos;
      opt_data->c3_cos_cache(j) += std::pow(s3, j) * c3_cos;
      opt_data->c1_sin_cache(j) += std::pow(s1, j) * c1_sin;
      opt_data->c3_sin_cache(j) += std::pow(s3, j) * c3_sin;
    }
  }

  // multiply with simpson-related terms to get the final integral
  opt_data->c1_cos_cache *= opt_data->ds1 / 3;
  opt_data->c2_cos_cache *= opt_data->ds2 / 3;
  opt_data->c3_cos_cache *= opt_data->ds3 / 3;
  opt_data->c1_sin_cache *= opt_data->ds1 / 3;
  opt_data->c2_sin_cache *= opt_data->ds2 / 3;
  opt_data->c3_sin_cache *= opt_data->ds3 / 3;

  // cache some other terms
  opt_data->psi1_f = opt_data->psi1.Evaluate(opt_data->sf1);
  opt_data->psi2_f = opt_data->psi2.Evaluate(opt_data->sf2);
  opt_data->psi3_f = opt_data->psi3.Evaluate(opt_data->sf3);
  opt_data->c1_f = opt_data->c1.Evaluate(opt_data->sf1);
  opt_data->c1_df = opt_data->c1_d.Evaluate(opt_data->sf1);
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GradX(double *grad, unsigned int n, OptData<double, degree_> *opt_data) {
  int num_poly_params = degree_;
  int idx;

  for(int i = 2; i <= degree_ + 1; ++i) {
    // for x1 w.r.t c1
    grad[i-2] += -opt_data->c1_sin_cache(i) / i;

    // for x2 w.r.t c1
    grad[i-2] += -(opt_data->sf1_pow(i) * opt_data->c2_sin_cache(0) / i + opt_data->sf1_pow(i-1) * opt_data->c2_sin_cache(1)); 
  
    // for x3 w.r.t c1
    grad[i-2] += -( (opt_data->sf1_pow(i)/i + opt_data->sf1_pow(i-1) * opt_data->sf2) * opt_data->c3_sin_cache(0) +
      opt_data->sf1_pow(i-1) * opt_data->c3_sin_cache(1) );

    // for x3 w.r.t c3
    idx = degree_ + i - 2;
    grad[idx] += -opt_data->c3_sin_cache(i) / i;
  }

  // for x1 w.r.t sf1
  grad[n-3] += std::cos(opt_data->psi1_f); 

  // for x2 w.r.t sf1
  grad[n-3] += -opt_data->c1_f * opt_data->c2_sin_cache(0) - 
    opt_data->c1_df * opt_data->c2_sin_cache(1);
  // for x2 w.r.t sf2
  grad[n-2] += std::cos(opt_data->psi2_f);

  // for x3 w.r.t sf1
  grad[n-3] += -(opt_data->c1_f + opt_data->c1_df * opt_data->sf2) * opt_data->c3_sin_cache(0) -
    opt_data->c1_df * opt_data->c3_sin_cache(1);
  // for x3 w.r.t sf2
  grad[n-2] += -opt_data->c1_f * opt_data->c3_sin_cache(0);
  // for x3 w.r.t sf3 
  grad[n-1] += std::cos(opt_data->psi3_f);

  // add in wind-related gradients
  grad[n-3] += opt_data->problem.vw_x / opt_data->problem.v;
  grad[n-2] += opt_data->problem.vw_x / opt_data->problem.v;
  grad[n-1] += opt_data->problem.vw_x / opt_data->problem.v;
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GradY(double *grad, unsigned int n, OptData<double, degree_> *opt_data) {
  int idx, start_idx(n);

  for(int i = 2; i <= degree_ + 1; ++i) {
    // for x1 w.r.t c1
    grad[start_idx+i-2] += opt_data->c1_cos_cache(i) / i;

    // for x2 w.r.t c1
    grad[start_idx+i-2] += opt_data->sf1_pow(i) * opt_data->c2_cos_cache(0) / i + 
      opt_data->sf1_pow(i-1) * opt_data->c2_cos_cache(1); 
  
    // for x3 w.r.t c1
    grad[start_idx+i-2] += (opt_data->sf1_pow(i)/i + opt_data->sf1_pow(i-1) * opt_data->sf2) * opt_data->c3_cos_cache(0) +
      opt_data->sf1_pow(i-1) * opt_data->c3_cos_cache(1);

    // for x3 w.r.t c3
    idx = start_idx + degree_ + i - 2;
    grad[idx] += opt_data->c3_cos_cache(i) / i;
  }

  // for x1 w.r.t sf1
  grad[start_idx+n-3] += std::sin(opt_data->psi1_f); 

  // for x2 w.r.t sf1
  grad[start_idx+n-3] += opt_data->c1_f * opt_data->c2_cos_cache(0) + 
    opt_data->c1_df * opt_data->c2_cos_cache(1);
  // for x2 w.r.t sf2
  grad[start_idx+n-2] += std::sin(opt_data->psi2_f);

  // for x3 w.r.t sf1
  grad[start_idx+n-3] += (opt_data->c1_f + opt_data->c1_df * opt_data->sf2) * opt_data->c3_cos_cache(0) +
    opt_data->c1_df * opt_data->c3_cos_cache(1);
  // for x3 w.r.t sf2
  grad[start_idx+n-2] += opt_data->c1_f * opt_data->c3_cos_cache(0);
  // for x3 w.r.t sf3 
  grad[start_idx+n-1] += std::sin(opt_data->psi3_f);

  // add in wind-related gradients
  grad[start_idx+n-3] += opt_data->problem.vw_y / opt_data->problem.v;
  grad[start_idx+n-2] += opt_data->problem.vw_y / opt_data->problem.v;
  grad[start_idx+n-1] += opt_data->problem.vw_y / opt_data->problem.v;
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GradPsi(double *grad, unsigned int n, OptData<double, degree_> *opt_data) {
  int idx, cos_start_id(2*n);

  for(int i = 2; i <= degree_+1; ++i) {
    // for psi w.r.t c1
    grad[cos_start_id+i-2] += opt_data->sf1_pow(i) / i + opt_data->sf1_pow(i-1) * 
      (opt_data->sf2 + opt_data->sf3);
    
    // for psi w.r.t c3
    idx = cos_start_id + degree_ + i - 2;
    grad[idx] += opt_data->sf3_pow(i) / i;
  }

  // for psi w.r.t sf1
  grad[cos_start_id+n-3] += opt_data->c1_f + opt_data->c1_df * (opt_data->sf2 + opt_data->sf3);

  // for psi w.r.t sf2
  grad[cos_start_id+n-2] += opt_data->c1_f;

  // for psi w.r.t sf3
  grad[cos_start_id+n-1] += opt_data->c3.Evaluate(opt_data->sf3);

  // populate gradients for sin and cos terms
  int sin_start_id(3*n);
  double cos_psi3f = std::cos(opt_data->psi3_f);
  double sin_psi3f = std::sin(opt_data->psi3_f);
  for(int i = 0; i < n; ++i) {
    grad[sin_start_id+i] = cos_psi3f * grad[cos_start_id+i];
    grad[cos_start_id+i] *= -sin_psi3f;
  }
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GradCurv(double *grad, unsigned int n, OptData<double, degree_> *opt_data) {
  int idx, start_idx(4*n);

  for(int i = 0; i < degree_; ++i) {
    // for curv w.r.t c1
    grad[start_idx+i] = opt_data->sf1_pow(i+1);

    // for curv w,r,t c3
    idx = start_idx + degree_ + i;
    grad[idx] += opt_data->sf3_pow(i+1);
  }

  // for curv w.r.t sf1
  grad[start_idx+n-3] += opt_data->c1_df;

  // for curv w.r.t sf3
  grad[start_idx+n-1] += opt_data->c3.Derivative().Evaluate(opt_data->sf3);
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
GradCurvDeriv(double *grad, unsigned int n, OptData<double, degree_> *opt_data) {
  int idx, start_idx(5*n);

  for(int i = 0; i < degree_; ++i) {
    grad[start_idx+i] += (i+1) * opt_data->sf1_pow(i) * opt_data->c1_df;
  }

  // w.r.t sf1
  Polynomial<double, degree_-1> c1_ddf = opt_data->c1_d.Derivative();
  grad[start_idx+n-3] += c1_ddf.Evaluate(opt_data->sf1) * opt_data->c1_df;
}

template <class T, size_t degree_>
void KiteBVPSolver<T, degree_>::
CurvConstraintFn(double *result, double *grad, unsigned int n, 
    OptData<double, degree_> *opt_data) {

  double s, c1_s, c1_ds, c3_s, c3_ds,
    max_curv_sq(opt_data->constraints.max_curv_sq),
    max_curv_rate_sq(opt_data->constraints.max_curv_rate_sq);
  int start_idx(6);
  int grad_start_id_1, grad_start_id_3, grad_start_id_d1, grad_start_id_d3;

  int num_s = opt_data->params.num_constraint_samples;
  for(int i = 0; i < num_s; ++i) {
    s = opt_data->s_vals(i);
    c1_s = opt_data->c1.Evaluate(s);
    c1_ds = opt_data->c1_d.Evaluate(s);
    c3_s = opt_data->c3.Evaluate(s);
    c3_ds = opt_data->c3_d.Evaluate(s);

    // populate result for c1
    result[start_idx+i] = 0.5 * (std::pow(c1_s, 2) - max_curv_sq);
    result[start_idx+i+num_s] = 0.5 * (std::pow(c1_ds, 2) - max_curv_rate_sq);

    // populate result for c3
    result[start_idx+i+2*num_s] = 0.5 * (std::pow(c3_s, 2) - max_curv_sq);
    result[start_idx+i+3*num_s] = 0.5 * (std::pow(c3_ds, 2) - max_curv_rate_sq);
  
    if(grad == NULL) {
      // nothing to do here
      continue;
    }

    // populate gradients
    grad_start_id_1 = (start_idx + i) * n; // for c1
    grad_start_id_d1 = (start_idx+i+num_s) * n; // for c1 derivative
    grad_start_id_3 = (start_idx+i+2*num_s) * n; // for c3
    grad_start_id_d3 = (start_idx+i+3*num_s) * n; // for c3 derivative

    grad[grad_start_id_1] = s;
    grad[grad_start_id_d1] = 1;
    grad[grad_start_id_3] = s;
    grad[grad_start_id_d3] = 1;

    for(int j = 1; j < degree_; ++j) {
      // for c1 and c2
      grad[grad_start_id_1+j] = grad[grad_start_id_3+j] = std::pow(s, j+1);

      // for c1_d and c2_d
      grad[grad_start_id_d1+j] = grad[grad_start_id_d3+j] = grad[grad_start_id_1+j-1] * (j+1);
    }

    // multiply with c1_s etc
    for(int j = 0; j < degree_; ++j) {
      grad[grad_start_id_1+j] *= c1_s;
      grad[grad_start_id_d1+j] *= c1_ds;
      grad[grad_start_id_3+j] *= c3_s;
      grad[grad_start_id_d3+j] *= c3_ds;
    }
  }
}

}
}