#include <stdio.h>
#include <math.h>
#include <iostream>
#include <stdlib.h>
#include "kite_bvp_solver/kite_bvp_solver.h"

using namespace ca;
namespace kite = kite_bvp_solver;

void test_terminal_error(kite::OptData<double, 4> *opt_data) {
  int num_terms = 5;
  double act_err[5];

  // read actual error from file
  FILE *f = fopen("/home/vdugar/dump/kite/term_err.txt", "r");
  for(int i = 0; i < num_terms; ++i) {
    fscanf(f, "%lf", &act_err[i]);
  }
  fclose(f);

  // compare
  for(int i = 0; i < num_terms; ++i) {
    double diff = std::abs(act_err[i] - opt_data->terminal_error[i]);
    if (diff > 1e-2) {
        std::cout << "Terminal error test FAILED with err: " << diff << "\n";
    } else {
        std::cout << "Terminal error test PASSED with err: " << diff << "\n";
    }
  }
}

void test_constraints(kite::KiteBVPSolver<double, 4> solver) {
  kite::OptData<double, 4> *opt_data = solver.opt_data_;
  double *constr_viol = new double[206];
  double *grad_constr = new double[206*11];

  // read params from file
  FILE *f = fopen("/home/vdugar/dump/kite/q.txt", "r");
  double *q = new double[11];
  for(int i = 0; i < 11; ++i) {
    fscanf(f, "%lf", &q[i]);
  }
  fclose(f);

  // read actual constr violations and gradients from file
  double act_constr_viol[6];
  f = fopen("/home/vdugar/dump/kite/constr_val.txt", "r");
  for(int i = 0; i < 6; ++i) {
    fscanf(f, "%lf", &act_constr_viol[i]);
  }
  fclose(f);
  f = fopen("/home/vdugar/dump/kite/constr_grad.txt", "r");
  double act_grad[66];
  for(int i = 0; i < 66; ++i) {
    fscanf(f, "%lf", &act_grad[i]);
  }
  fclose(f);

  // update solver
  solver.UpdateOptData(solver.opt_data_, std::max(q[8], q[10]) * 2);
  solver.opt_data_->problem = solver.problem_;

  // get gradients from solver
  kite::KiteBVPSolver<double, 4>::ConstraintFn(206, constr_viol, 11, q, grad_constr,
    static_cast<void*>(opt_data));

  // test terminal error 
  test_terminal_error(opt_data);

  std::cout << "\n************\n";

  // test constr violations
  for(int i = 0; i < 6; ++i) {
    double diff = std::abs(act_constr_viol[i] - constr_viol[i]);
    if (diff > 1e-2) {
        std::cout << "Constr viol test FAILED with err: " << diff << "\n";
    } else {
        std::cout << "Constr viol test PASSED with err: " << diff << "\n";
    }
  }

  std::cout << "\n************\n";

  // test constr grad
  for(int i = 0; i < 66; ++i) {
    double diff = std::abs(act_grad[i] - grad_constr[i]);
    if (diff > 1e-2) {
        std::cout << "Constr grad test FAILED at idx " << i << " with err: " << diff << "\n";
    }
  }

  std::cout << "\n************\n";
}

void dump_stuff(kite::KiteBVPSolver<double, 4> solver) {
  // account for wind
  bool valid;

  int n = 11;
  kite::OptData<double, 4> *opt_data = solver.opt_data_;
  solver.GetInitGuess();
  solver.UpdateOptData(opt_data, 
    std::max(solver.init_guess_[solver.num_params_-3], solver.init_guess_[solver.num_params_-1]) * 2);

  kite::KiteBVPSolver<double, 4>::UnpackParams(solver.init_guess_.data(), n, opt_data);
  kite::KiteBVPSolver<double, 4>::PreCompute(opt_data);
  kite::KiteBVPSolver<double, 4>::GetTerminalError(opt_data);

  // dump stuff to file
  // sin and cos caches
  FILE *f1 = fopen("/home/vdugar/dump/kite/cpp/c1_cos_cache.txt", "w");
  FILE *f2 = fopen("/home/vdugar/dump/kite/cpp/c3_cos_cache.txt", "w");
  FILE *f3 = fopen("/home/vdugar/dump/kite/cpp/c1_sin_cache.txt", "w");
  FILE *f4 = fopen("/home/vdugar/dump/kite/cpp/c3_sin_cache.txt", "w");
  for(int i = 0; i < 6; ++i) {
    fprintf(f1, "%lf\n", opt_data->c1_cos_cache(i));
    fprintf(f2, "%lf\n", opt_data->c3_cos_cache(i));
    fprintf(f3, "%lf\n", opt_data->c1_sin_cache(i));
    fprintf(f4, "%lf\n", opt_data->c3_sin_cache(i));
  }
  fclose(f1); fclose(f2); fclose(f3); fclose(f4);
  f1 = fopen("/home/vdugar/dump/kite/cpp/c2_cos_cache.txt", "w");
  f2 = fopen("/home/vdugar/dump/kite/cpp/c2_sin_cache.txt", "w");
  fprintf(f1, "%lf\n%lf\n", opt_data->c2_cos_cache(0), opt_data->c2_cos_cache(1));
  fprintf(f2, "%lf\n%lf\n", opt_data->c2_sin_cache(0), opt_data->c2_sin_cache(1));
  fclose(f1); fclose(f2);

  // dump simpson weights
  f1 =fopen("/home/vdugar/dump/kite/cpp/weights.txt", "w");
  for(int i = 0; i < solver.params_.num_simpson_samples; ++i) {
    fprintf(f1, "%lf\n", opt_data->simpson_wts(i));
  }
  fclose(f1);

  // dump power terms
  f1 =fopen("/home/vdugar/dump/kite/cpp/pow.txt", "w");
  for(int i = 0; i < 6; ++i) {
    fprintf(f1, "%lf,%lf\n", opt_data->sf1_pow(i), opt_data->sf3_pow(i));
  }
  fclose(f1);

  // dump terminal err
  f1 = fopen("/home/vdugar/dump/kite/cpp/terminal_error.txt", "w");
  for(int i = 0; i < opt_data->terminal_error.size(); ++i) {
    fprintf(f1, "%lf\n", opt_data->terminal_error[i]);
  }
  fclose(f1);

  int m = 6+8*solver.params_.num_constraint_samples;
  double *result = new double[m];
  double *grad = new double[m*n];

  // get constraint terms
  kite::KiteBVPSolver<double, 4>::ConstraintFn(m,
    result, n, solver.init_guess_.data(), grad, static_cast<void *>(opt_data));
  f1 = fopen("/home/vdugar/dump/kite/cpp/constr.txt", "w");
  for(int i = 0; i < m; ++i) {
    fprintf(f1, "%lf\n", result[i]);
  }
  fclose(f1);
  f1 = fopen("/home/vdugar/dump/kite/cpp/constr_grad.txt", "w");
  for(int i = 0; i < m*n; ++i) {
    fprintf(f1, "%lf\n", grad[i]);
  }
  fclose(f1);

  // dump ineq terms
  // kite::KiteBVPSolver<double, 4>::CurvConstraintFn(result, grad, solver.init_guess_.data(), n,
  //   opt_data);
  // f1 = fopen("/home/vdugar/dump/kite/cpp/A_ineq.txt", "w");
  // for(int i = 6; i < 6 + 8*solver.params_.num_constraint_samples; ++i) {
  //   fprintf(f1, "%lf\n", result[i]);
  // }
  // fclose(f1);
  // f1 = fopen("/home/vdugar/dump/kite/cpp/grad_ineq.txt", "w");
  // for(int i = 6*n; i < (6+8*solver.params_.num_constraint_samples)*n; ++i) {
  //   fprintf(f1, "%lf\n", grad[i]);
  // }
  // fclose(f1);
}

int main(int argc, char **argv) {
    // Define params
    kite::Params params;
    params.num_constraint_samples = 50;
    params.num_simpson_samples = 101;
    params.bv_tol[0] = 1e-3;
    params.bv_tol[1] = 1e-3;
    params.bv_tol[2] = 1e-3;
    params.bv_tol[3] = 1e-3;
    params.bv_tol[4] = 1e-4;
    params.curv1_tol = 1e-4;
    params.precision = 2;
    params.constraint_tol = 1e-6;

    // Define consraints
    kite::Constraints constraints;
    constraints.max_curv = 1./20.;
    constraints.max_curv_rate = 1./20.;

    // Set up problem
    kite::BVProblem problem;
    problem.X0[0] = 0;
    problem.X0[1] = 0;
    problem.X0[2] = 0;
    problem.X0[3] = 0;
    problem.Xf[0] = 60;
    problem.Xf[1] = 70;
    problem.Xf[2] = M_PI / 2;
    problem.Xf[3] = 0;
    problem.v = 50;
    problem.vw_x = 10;
    problem.vw_y = 10;

    // other params
    double step_size = 0.1;

    // declare solver object
    Eigen::MatrixXd path;
    bool valid;
    double cost;
    kite::KiteBVPSolver<double, 4> solver;
    solver.Initialize(params, constraints);
    solver.problem_ = problem;
    solver.problem_.Xf[2] = kite::GetAirframeHeading(solver.problem_.v, solver.problem_.Xf[2], 
      solver.problem_.vw_x, solver.problem_.vw_y, valid);
    std::cout << "new heading: " << solver.problem_.Xf[2] << "\n";
    solver.opt_data_->problem = solver.problem_;

    // run tests
    // test_constraints(solver);

    dump_stuff(solver);
}