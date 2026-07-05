#ifndef KITE_BVP_SOLVER_INCLUDE_CONSTR_H
#define KITE_BVP_SOLVER_INCLUDE_CONSTR_H
#include "kite_bvp_defs.h"
#include "utils.h"


#include <roboptim/core/io.hh>
#include <roboptim/core/solver.hh>
#include <roboptim/core/alloc.hh>

#include <roboptim/core/plugin/ipopt/ipopt.hh>
#include <roboptim/core/differentiable-function.hh>
#include <roboptim/core/solver-factory.hh>
#include "matplotlibcpp.h"


namespace plt = matplotlibcpp;

namespace ro = roboptim;
namespace ca {
    namespace kite_bvp_solver {
        template<class T, size_t degree_>
        struct G : public ro::DifferentiableFunction {

            Params params;
            Constraints constraints;
            BVProblem problem;
            OptData<double, degree_> *opt_data_;
            unsigned num_params;
            unsigned m;


            G(Params &params_, Constraints &constraints_, BVProblem &problem_ , std::vector<double> &init_guess_) : ro::DifferentiableFunction(2 * degree_ + 3, 6 + 8 *params_.num_constraint_samples,"Constraints") {
                params = params_;
                constraints = constraints_;
                problem = problem_;
                opt_data_ = new OptData<double, degree_>;
                num_params = 2 * degree_ + 3;
                m = 6 + 8 *params_.num_constraint_samples;
                InitOptData(opt_data_);
                UpdateOptData(opt_data_, std::max(init_guess_[num_params - 3], init_guess_[num_params - 1]) * 2);


            }

            void InitOptData(OptData<double, degree_> *opt_data) {
                opt_data->params = params;
                opt_data->constraints = constraints;
                opt_data->problem = problem;
                opt_data->count = 0;
                // initialize linear inequality terms
                opt_data->A = Eigen::MatrixXd::Zero(8 * params.num_constraint_samples, num_params);
                opt_data->b = Eigen::VectorXd::Zero(8 * params.num_constraint_samples);

                // initialize caches
                opt_data->c1_cos_cache = Eigen::VectorXd::Constant(degree_ + 2, 0);
                opt_data->c2_cos_cache = Eigen::VectorXd::Constant(2, 0);
                opt_data->c3_cos_cache = Eigen::VectorXd::Constant(degree_ + 2, 0);
                opt_data->c1_sin_cache = Eigen::VectorXd::Constant(degree_ + 2, 0);
                opt_data->c2_sin_cache = Eigen::VectorXd::Constant(2, 0);
                opt_data->c3_sin_cache = Eigen::VectorXd::Constant(degree_ + 2, 0);
                opt_data->sf1_pow = Eigen::VectorXd::Constant(degree_ + 2, 0);
                opt_data->sf3_pow = Eigen::VectorXd::Constant(degree_ + 2, 0);

                // set simpson weights
                opt_data->simpson_wts = Eigen::VectorXd::Constant(params.num_simpson_samples, 0);
                opt_data->simpson_wts(0) = 1;
                opt_data->simpson_wts(1) = 4;
                opt_data->simpson_wts(params.num_simpson_samples - 1) = 1;
                for (int i = 2; i <= params.num_simpson_samples - 2; ++i) {
                    opt_data->simpson_wts(i) = (i % 2 == 0) ? 2 : 4;
                }
            }


            void impl_compute(result_ref result, const_argument_ref x) const {


                UnpackParams(x.data(), num_params, opt_data_);

                // Pre-compute and cache a bunch of terms that we'll keep using
                PreCompute(opt_data_);

                // Populate the constraint violation
                GetTerminalError(opt_data_);

                result[0] = 0.5 * std::pow(opt_data_->terminal_error[0], 2) - opt_data_->params.bv_tol[0];//x
                result[1] = 0.5 * std::pow(opt_data_->terminal_error[1], 2) - opt_data_->params.bv_tol[1];//y
                result[2] = 0.5 * std::pow(opt_data_->terminal_error[2], 2) - opt_data_->params.bv_tol[2];//*L, phi
                result[3] = (0.5 * std::pow(opt_data_->terminal_error[3], 2) - opt_data_->params.bv_tol[3]);//*L, phi
                result[4] = (0.5 * std::pow(opt_data_->terminal_error[4], 2) - opt_data_->params.bv_tol[4]); //final curvature
                result[5] = (0.5 * std::pow(opt_data_->c1_df, 2) - opt_data_->params.curv1_tol);

                Eigen::VectorXd res = opt_data_->A * x - opt_data_->b;

                int num_s = 8 * opt_data_->params.num_constraint_samples;
                int start_idx = 6;

                for (int i = 0; i < num_s; ++i) {
                    result[i + start_idx] = res(i);
                }

            }

            void impl_gradient (gradient_ref grad, const_argument_ref x, size_type id) const

            {
                grad.fill(0.0);



//                double *grad_;
                unsigned n = num_params;
                // zero out gradients first
//                memset(grad_, 0, m * n * sizeof(double)); // TODO - check
                // compute gradients for each of the boundary value inequality constraints
                switch (id) {
                    case 0:
                        UnpackParams(x.data(), num_params, opt_data_);

                        // Pre-compute and cache a bunch of terms that we'll keep using
                        PreCompute(opt_data_);

                        // Populate the constraint violation
                        GetTerminalError(opt_data_);

//                        std::cout << "1" << std::endl;
                        GradX(grad, n, opt_data_);
                        break;
                    case 1:
//                        std::cout << "2" << std::endl;

                        GradY(grad, n, opt_data_);
                        break;
                    case 2:
//                        std::cout << "3" << std::endl;

                        GradPsiCos(grad, n, opt_data_);
                        break;
                    case 3:
//                        std::cout << "4" << std::endl;

                        GradPsiSin(grad, n, opt_data_);
                        break;
                    case 4:
                        GradCurv(grad, n, opt_data_);
                        break;
                    case 5:
                        // compute gradient for c1_df
                        GradCurvDeriv(grad, n, opt_data_);
                        break;
                    default:
                        assert(id>5 && "Oops");
                        for (int j = 0; j < n; ++j) {
                            grad[j] = opt_data_->A(id-6, j);
                        }
                        break;
                }


//



            }
            static void GradX(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int num_poly_params = degree_;
                int idx;
                //   grad(0) = 22.0;



                for (int i = 2; i <= degree_ + 1; ++i) {
                    // for x1 w.r.t c1
                    grad(i - 2) += -opt_data->c1_sin_cache(i) / i;

                    // for x2 w.r.t c1
                    grad(i - 2) += -(opt_data->sf1_pow(i) * opt_data->c2_sin_cache(0) / i +
                                     opt_data->sf1_pow(i - 1) * opt_data->c2_sin_cache(1));

                    // for x3 w.r.t c1
                    grad(i - 2) += -((opt_data->sf1_pow(i) / i + opt_data->sf1_pow(i - 1) * opt_data->sf2) *
                                     opt_data->c3_sin_cache(0) +
                                     opt_data->sf1_pow(i - 1) * opt_data->c3_sin_cache(1));

                    // for x3 w.r.t c3
                    idx = degree_ + i - 2; // 4,5,6,7
                    grad(idx) += -opt_data->c3_sin_cache(i) / i;
                }

                // for x1 w.r.t sf1
                grad(n - 3) += std::cos(opt_data->psi1_f);

                // for x2 w.r.t sf1
                grad(n - 3) += -opt_data->c1_f * opt_data->c2_sin_cache(0) -
                               opt_data->c1_df * opt_data->c2_sin_cache(1);
                // for x2 w.r.t sf2
                grad(n - 2) += std::cos(opt_data->psi2_f);

                // for x3 w.r.t sf1
                grad(n - 3) += -(opt_data->c1_f + opt_data->c1_df * opt_data->sf2) * opt_data->c3_sin_cache(0) -
                               opt_data->c1_df * opt_data->c3_sin_cache(1);
                // for x3 w.r.t sf2
                grad(n - 2) += -opt_data->c1_f * opt_data->c3_sin_cache(0);
                // for x3 w.r.t sf3
                grad(n - 1) += std::cos(opt_data->psi3_f);

                // add in wind-related gradients
                grad(n - 3) += opt_data->problem.vw_x / opt_data->problem.v;
                grad(n - 2) += opt_data->problem.vw_x / opt_data->problem.v;
                grad(n - 1) += opt_data->problem.vw_x / opt_data->problem.v;

                // scale gradient with err_x
                for (int i = 0; i < n; ++i) {
                    grad(i) *= opt_data->terminal_error[0];
                }
//            print_grad(n, grad);
            }




            static void GradY(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int idx, start_idx(0);
                for (int i = 2; i <= degree_ + 1; ++i) {
                    // for x1 w.r.t c1
                    grad[start_idx + i - 2] += opt_data->c1_cos_cache(i) / i;

                    // for x2 w.r.t c1
                    grad[start_idx + i - 2] += opt_data->sf1_pow(i) * opt_data->c2_cos_cache(0) / i +
                                               opt_data->sf1_pow(i - 1) * opt_data->c2_cos_cache(1);

                    // for x3 w.r.t c1
                    grad[start_idx + i - 2] += (opt_data->sf1_pow(i) / i + opt_data->sf1_pow(i - 1) * opt_data->sf2) *
                                               opt_data->c3_cos_cache(0) +
                                               opt_data->sf1_pow(i - 1) * opt_data->c3_cos_cache(1);

                    // for x3 w.r.t c3
                    idx = start_idx + degree_ + i - 2;
                    grad[idx] += opt_data->c3_cos_cache(i) / i;
                }

                // for x1 w.r.t sf1
                grad[start_idx + n - 3] += std::sin(opt_data->psi1_f);

                // for x2 w.r.t sf1
                grad[start_idx + n - 3] += opt_data->c1_f * opt_data->c2_cos_cache(0) +
                                           opt_data->c1_df * opt_data->c2_cos_cache(1);
                // for x2 w.r.t sf2
                grad[start_idx + n - 2] += std::sin(opt_data->psi2_f);

                // for x3 w.r.t sf1
                grad[start_idx + n - 3] += (opt_data->c1_f + opt_data->c1_df * opt_data->sf2) * opt_data->c3_cos_cache(0) +
                                           opt_data->c1_df * opt_data->c3_cos_cache(1);
                // for x3 w.r.t sf2
                grad[start_idx + n - 2] += opt_data->c1_f * opt_data->c3_cos_cache(0);
                // for x3 w.r.t sf3
                grad[start_idx + n - 1] += std::sin(opt_data->psi3_f);

                // add in wind-related gradients
                grad[start_idx + n - 3] += opt_data->problem.vw_y / opt_data->problem.v;
                grad[start_idx + n - 2] += opt_data->problem.vw_y / opt_data->problem.v;
                grad[start_idx + n - 1] += opt_data->problem.vw_y / opt_data->problem.v;

                // scale gradient with err_y
                for (int i = start_idx; i < start_idx + n; ++i) {
                    grad[i] *= opt_data->terminal_error[1];
                }
            }


            static void GradPsiCos(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int idx, cos_start_id(0);

                for (int i = 2; i <= degree_ + 1; ++i) {
                    // for psi w.r.t c1
                    grad[cos_start_id + i - 2] += opt_data->sf1_pow(i) / i + opt_data->sf1_pow(i - 1) *
                                                                             (opt_data->sf2 + opt_data->sf3);

                    // for psi w.r.t c3
                    idx = cos_start_id + degree_ + i - 2;
                    grad[idx] += opt_data->sf3_pow(i) / i;
                }

                // for psi w.r.t sf1
                grad[cos_start_id + n - 3] += opt_data->c1_f + opt_data->c1_df * (opt_data->sf2 + opt_data->sf3);

                // for psi w.r.t sf2
                grad[cos_start_id + n - 2] += opt_data->c1_f;

                // for psi w.r.t sf3
                grad[cos_start_id + n - 1] += opt_data->c3.Evaluate(opt_data->sf3);

                // populate gradients for sin and cos terms, and scale with terminal error
                double sin_psi3f = std::sin(opt_data->psi3_f);
                for (int i = 0; i < n; ++i) {
                    grad[cos_start_id + i] *= -sin_psi3f * opt_data->terminal_error[2];
                }
            }

            static void GradPsiSin(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int idx, cos_start_id(0);

                for (int i = 2; i <= degree_ + 1; ++i) {
                    // for psi w.r.t c1
                    grad[cos_start_id + i - 2] += opt_data->sf1_pow(i) / i + opt_data->sf1_pow(i - 1) *
                                                                             (opt_data->sf2 + opt_data->sf3);

                    // for psi w.r.t c3
                    idx = cos_start_id + degree_ + i - 2;
                    grad[idx] += opt_data->sf3_pow(i) / i;
                }

                // for psi w.r.t sf1
                grad[cos_start_id + n - 3] += opt_data->c1_f + opt_data->c1_df * (opt_data->sf2 + opt_data->sf3);

                // for psi w.r.t sf2
                grad[cos_start_id + n - 2] += opt_data->c1_f;

                // for psi w.r.t sf3
                grad[cos_start_id + n - 1] += opt_data->c3.Evaluate(opt_data->sf3);

                // populate gradients for sin and cos terms, and scale with terminal error
                int sin_start_id(0);
                double cos_psi3f = std::cos(opt_data->psi3_f);
                for (int i = 0; i < n; ++i) {
                    grad[sin_start_id + i] = cos_psi3f * grad[cos_start_id + i] * opt_data->terminal_error[3];
                }
            }


            static void GradCurv(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int idx, start_idx(0);

                for (int i = 0; i < degree_; ++i) {
                    // for curv w.r.t c1
                    grad[start_idx + i] = opt_data->sf1_pow(i + 1);

                    // for curv w,r,t c3
                    idx = start_idx + degree_ + i;
                    grad[idx] += opt_data->sf3_pow(i + 1);
                }

                // for curv w.r.t sf1
                grad[start_idx + n - 3] += opt_data->c1_df;

                // for curv w.r.t sf3
                grad[start_idx + n - 1] += opt_data->c3.Derivative().Evaluate(opt_data->sf3);

                // scale gradient with err_curv
                for (int i = start_idx; i < start_idx + n; ++i) {
                    grad[i] *= opt_data->terminal_error[4];
                }
            }


            static void GradCurvDeriv(gradient_ref grad, unsigned int n, OptData<double, degree_> *opt_data) {
                int idx, start_idx(0);

                for (int i = 0; i < degree_; ++i) {
                    grad[start_idx + i] += (i + 1) * opt_data->sf1_pow(i) * opt_data->c1_df;
                }

                // w.r.t sf1
                // Polynomial<double, degree_-1> c1_ddf = opt_data->c1_d.Derivative();
                grad[start_idx + n - 3] += opt_data->c1_d.Derivative().Evaluate(opt_data->sf1) * opt_data->c1_df;
            }



            static void PreCompute(OptData<double, degree_> *opt_data) {
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
                opt_data->ds1 = opt_data->sf1 / (opt_data->params.num_simpson_samples - 1);
                opt_data->ds2 = opt_data->sf2 / (opt_data->params.num_simpson_samples - 1);
                opt_data->ds3 = opt_data->sf3 / (opt_data->params.num_simpson_samples - 1);

                // generate and cache powers of sf1, sf2 and sf3
                opt_data->sf1_pow(0) = 1;
                opt_data->sf3_pow(0) = 1;
                for (int i = 1; i <= degree_ + 1; ++i) {
                    opt_data->sf1_pow(i) = std::pow(opt_data->sf1, i);
                    opt_data->sf3_pow(i) = std::pow(opt_data->sf3, i);
                }

                // generate and cache integral terms
                for (int i = 0; i < opt_data->params.num_simpson_samples; ++i) {
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
                    for (int j = 1; j <= degree_ + 1; ++j) {
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

            static void GetTerminalError(OptData<double, degree_> *opt_data) {
                // get terminal X, Y, psi and curv vals
                double sf = opt_data->sf1 + opt_data->sf2 + opt_data->sf3;
                double x_f = opt_data->c1_cos_cache(0) + opt_data->c2_cos_cache(0) + opt_data->c3_cos_cache(0) +
                             sf * opt_data->problem.vw_x / opt_data->problem.v;
                double y_f = opt_data->c1_sin_cache(0) + opt_data->c2_sin_cache(0) + opt_data->c3_sin_cache(0) +
                             sf * opt_data->problem.vw_y / opt_data->problem.v;
                double psi_f = opt_data->psi3.Evaluate(opt_data->sf3);
                double curv_f = opt_data->c3.Evaluate(opt_data->sf3);
                double L = 1.2;//1/0.0872665;
                opt_data->terminal_error[0] = x_f - opt_data->problem.Xf[0];
                opt_data->terminal_error[1] = y_f - opt_data->problem.Xf[1];
                opt_data->terminal_error[2] = L * L * (std::cos(psi_f) - std::cos(opt_data->problem.Xf[2]));
                opt_data->terminal_error[3] = L * L * (std::sin(psi_f) - std::sin(opt_data->problem.Xf[2]));
                opt_data->terminal_error[4] = L * L * L * L * (curv_f - opt_data->problem.Xf[3]);

//                std::cout << opt_data->terminal_error[0] << std::endl;

            }

            void UpdateOptData(OptData<double, degree_> *opt_data, double s_max) {
                double s;
                int start_idx;
                Eigen::VectorXd s_vals = Eigen::VectorXd::LinSpaced(
                        Eigen::Sequential, params.num_constraint_samples, 0, s_max);

                // populate linear inequality terms
                for (int i = 0; i < params.num_constraint_samples; ++i) {
                    s = s_vals(i);
                    for (int j = 0; j < degree_; ++j) {
                        // for C1
                        opt_data->A(i, j) = std::pow(s, j + 1);
                        opt_data->A(i + params.num_constraint_samples, j) = -opt_data->A(i, j);
                        opt_data->b(i) = opt_data->b(i + params.num_constraint_samples) = opt_data->constraints.max_curv;

                        // for C3
                        start_idx = 2 * params.num_constraint_samples;
                        opt_data->A(i + start_idx, j + degree_) = opt_data->A(i, j);
                        opt_data->A(i + start_idx + params.num_constraint_samples, j + degree_) = -opt_data->A(i, j);
                        opt_data->b(i + start_idx) = opt_data->b(i + start_idx + params.num_constraint_samples) =
                                opt_data->constraints.max_curv;

                        // for C1_deriv
                        start_idx = 4 * params.num_constraint_samples;
                        opt_data->A(i + start_idx, j) = (j + 1) * std::pow(s, j);
                        opt_data->A(i + start_idx + params.num_constraint_samples, j) = -opt_data->A(i + start_idx, j);
                        opt_data->b(i + start_idx) = opt_data->b(i + start_idx + params.num_constraint_samples) =
                                opt_data->constraints.max_curv_rate;

                        // for C3_deriv
                        start_idx = 6 * params.num_constraint_samples;
                        opt_data->A(i + start_idx, j + degree_) = opt_data->A(i + 4 * params.num_constraint_samples, j);
                        opt_data->A(i + start_idx + params.num_constraint_samples, j + degree_) =
                                -opt_data->A(i + 4 * params.num_constraint_samples, j);
                        opt_data->b(i + start_idx) = opt_data->b(i + start_idx + params.num_constraint_samples) =
                                opt_data->constraints.max_curv_rate;
                    }
                }
            }
            static void UnpackParams(const double *p, unsigned int n, OptData<double, degree_> *opt_data) {
                int num_poly_params = degree_;
                BVProblem problem = opt_data->problem;

                // extract distances
                opt_data->sf1 = p[n - 3];
                opt_data->sf2 = p[n - 2];
                opt_data->sf3 = p[n - 1];

                // create curvature polys
                opt_data->c1[0] = problem.X0[3]; // set to initial curvature
                for (int i = 0; i < num_poly_params; ++i) {
                    opt_data->c1[i + 1] = p[i];
                    opt_data->c3[i + 1] = p[i + num_poly_params];
                }
                opt_data->c2[0] = opt_data->c1.Evaluate(opt_data->sf1);
                opt_data->c3[0] = opt_data->c2.Evaluate(opt_data->sf2);
                // create heading polys
                opt_data->psi1.SetToIntegral(opt_data->c1, problem.X0[2]);
                opt_data->psi2.SetToIntegral(opt_data->c2, opt_data->psi1.Evaluate(opt_data->sf1));
                opt_data->psi3.SetToIntegral(opt_data->c3, opt_data->psi2.Evaluate(opt_data->sf2));

                // create derivative polys
                opt_data->c1_d.SetToDerivative(opt_data->c1);
                opt_data->c3_d.SetToDerivative(opt_data->c3);
            }

            void plot(std::vector<double> &q, unsigned num_params_, double step_size, const char *name) {
                // Plot
                UnpackParams(q.data(), num_params_, opt_data_);
                double sf = opt_data_->sf1 + opt_data_->sf2 + opt_data_->sf3;
                unsigned num_path = int(sf / step_size) + 2;
                std::vector<Polynomial<double, degree_>> curv_polys = {opt_data_->c1, opt_data_->c2, opt_data_->c3};
                std::vector<Polynomial<double, degree_ + 1>> psi_polys = {opt_data_->psi1, opt_data_->psi2,
                                                                          opt_data_->psi3};
                std::vector<double> breaks = {0, opt_data_->sf1, opt_data_->sf1 + opt_data_->sf2, sf};

                // evaluate solution to get path
                std::vector<double> path_x, path_y;
                double prev_x(0), prev_y(0), s(0), curv, psi, x, y, cos_psi, sin_psi, prev_cos, prev_sin;
                int curr_id(0);
                path_x.push_back(problem.X0[0]);
                path_y.push_back(problem.X0[1]);
                prev_cos = std::cos(psi_polys[curr_id].Evaluate(0));
                prev_sin = std::sin(psi_polys[curr_id].Evaluate(0));
                while (s <= sf) {
                    // check which poly we should evaluate
                    if (s > breaks[curr_id + 1]) {
                        // move on to the next poly
                        ++curr_id;
                    }

//                curv = curv_polys[curr_id].Evaluate(s - breaks[curr_id]);
                    psi = ca::math_utils::angular_math::WrapTo2Pi(problem.X0[2] +
                                                                  psi_polys[curr_id].Evaluate(s - breaks[curr_id]));
                    cos_psi = std::cos(psi);
                    sin_psi = std::sin(psi);

                    // perform integrations using the trapezoidal rule (accurate enough?)
                    x = path_x.back() + step_size * (cos_psi + prev_cos) / 2 +
                        problem.vw_x * step_size / problem.v;
                    y = path_y.back() + step_size * (sin_psi + prev_sin) / 2 +
                        problem.vw_y * step_size / problem.v;
                    path_x.push_back(x);
                    path_y.push_back(y);
//                path(path_id, 2) = psi;
//                path(path_id, 3) = curv;
                    prev_cos = cos_psi;
                    prev_sin = sin_psi;
                    s += step_size;
                }
                plt::title("Final path");
                plt::named_plot(name, path_x, path_y);
                plt::axis("equal");
                plt::plot({problem.X0[0]}, {problem.X0[1]}, "r*");
                plt::plot({problem.Xf[0]}, {problem.Xf[1]}, "g*");
                plt::legend();
            }



        };
    }
}
#endif