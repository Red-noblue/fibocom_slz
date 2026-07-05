#ifndef KITE_BVP_SOLVER_INCLUDE_SOLVER_H
#define KITE_BVP_SOLVER_INCLUDE_SOLVER_H

#include "utils.h"
#include "kite_bvp_defs.h"
#include "obj.h"
#include "constr.h"
#include "guess.h"
#include <roboptim/core/io.hh>
#include <roboptim/core/solver.hh>
#include <roboptim/core/alloc.hh>
#include <map>
#include <fstream>
#include "ros/ros.h"
#include "ros/package.h"
#include <roboptim/core/plugin/ipopt/ipopt.hh>
#include <roboptim/core/differentiable-function.hh>
#include <roboptim/core/solver-factory.hh>
#include "matplotlibcpp.h"

namespace plt = matplotlibcpp;
namespace ro = roboptim;
namespace ca {
    namespace kite_bvp_solver {
        template<class T, size_t degree_>
        class Solver {
        public:
            bool success;
            std::vector<double> init_guess_;
            //            std::vector<double> tol_;
            double tol_;
            unsigned num_params, m;
            Params params;
            Constraints constraints;
            BVProblem problem;
            boost::shared_ptr<Init> init;
            std::vector<double> solution;
            double seed_time, solve_time; // todo remove this

            Solver(Params &params_, Constraints &constraints_ ,std::string &filename){
                params = params_;
                tol_ = params.constraint_tol;
                constraints = constraints_;
                num_params = 2 * degree_ + 3;
                m = 6 + 8 *params_.num_constraint_samples;
                //                init_guess = boost::make_shared<Init>(new Init(filename));
                init = boost::shared_ptr<Init>(new Init(filename));
                seed_time = 0;
                solve_time = 0;
            }

            ~Solver(){
            }
            bool multisolve(BVProblem &problem_, double wind[2]){
                success = false;
                int trial = 0;
                auto og_problem = problem_;
                init->reset();
                while (trial < 9) {
                    std::cout<<trial<<std::endl;
                    init->getInitWind(problem_, wind);
                    init_guess_ = init->init_guess;
                    og_problem.vw_x = wind[0];
                    og_problem.vw_y = wind[1];
                    if (solve(og_problem)) {
                        init->reset();
                        return true;
                    }
                    else
                        trial++;
                }
                std::cout<< "Failed.. trying again" <<std::endl;
                init->reset();
                init->getInitWind(og_problem, wind);
                solution = init->init_guess;
                init->reset();
                std::cout<< "Failed.. returning init" <<std::endl;
                return false;

            };
            std::vector<double> bitsolve(BVProblem &problem_){

                //                bool valid;

                init->reset();
                int trial = 0;
                while (trial < 10) {
                    std::cout<<trial<<std::endl;

                    if(init->getInit(problem_)) {


                        init_guess_ = init->init_guess;
                    }
                    else{
                        std::cout<<"no seed";
                        assert(0);
                    }
                    if (solve(problem_)) {
                        return solution;
                    } else {
                        trial++;

                    }

                }

                std::cout<< "Failed" <<std::endl;
                if (init->getCloseInit(problem_))
                {
                    init_guess_ = init->init_guess;
                    return init_guess_;

                } else
                {
                    init->getRandInit(problem_);
                    init_guess_ = init->init_guess;
                    return init_guess_;


                }



            };

            bool solve(BVProblem &problem_)

            {
                bool valid;
                problem = problem_;
//                            problem.Xf[2] = GetAirframeHeading(problem.v, problem.Xf[2], problem.vw_x,
//                                    problem.vw_y, valid);
//                            assert(valid && "No heading");
                //

                //                std::cout<<init_guess_[0] <<std::endl;
                typedef ro::Solver<ro::EigenMatrixDense> solver_t;
                boost::shared_ptr<F<double,degree_>>f (new F<double,degree_> ());
                boost::shared_ptr<G<double,degree_>>g (new G<double,degree_> (params, constraints , problem, init_guess_));
//                            g->plot(init_guess_, num_params, 0.01, (const char *) "Init path");
//                            double wind[] = {problem.vw_x,problem.vw_y};
//                            init->getInitWind(problem, wind);
//                            init_guess_ = init->init_guess;
//                            g->plot(init_guess_, num_params, 0.01, (const char *) "Init path");
//
//                            plt::show();

                solver_t::problem_t pb (f);
                ro::Function::vector_t start (pb.function ().inputSize ());
                for (ro::Function::size_type i = 0; i < pb.function ().inputSize (); ++i){
                    start[i] = init_guess_[i];
                    if (i <= num_params - 4) {
                        // poly coeffs
                        pb.argumentBounds ()[i] = ro::Function::makeInterval (-1e-2, 1e-2);
                    } else {
                        // arc lengths
                        pb.argumentBounds ()[i] = ro::Function::makeInterval (0, 2*abs(init_guess_[i]));
                    }
                }


                pb.startingPoint() = start;
                F<double,4>::intervals_t bounds;
                solver_t::problem_t::scaling_t scaling;
                bounds.clear();
                for( unsigned int i=0; i< m; ++i ){
                    bounds.push_back(ro::Function::makeUpperInterval (tol_));
                    scaling.push_back (1.0);
                }

                pb.addConstraint(boost::static_pointer_cast<ro::DifferentiableFunction> (g),bounds, scaling);

                ro::SolverFactory<solver_t> factory ("ipopt", pb);
                factory().parameters()["ipopt.acceptable_iter"].value = 2;
//                          factory().parameters ()["ipopt.linear_solver"].value = std::string ("ma97");
                factory().parameters()["ipopt.tol"].value = 1e-1;
                factory().parameters()["ipopt.acceptable_tol"].value = 1e-1;
                factory().parameters()["ipopt.acceptable_obj_change_tol"].value = 1e-2;
                factory().parameters()["ipopt.obj_change_tol"].value = 1e-1;
                factory().parameters()["ipopt.constr_viol_tol"].value = 1e-1;
                factory().parameters()["ipopt.acceptable_constr_viol_tol"].value = 1e-1;

                factory().parameters()["ipopt.dual_inf_tol"].value = 1e+10;
                factory().parameters()["ipopt.nlp_scaling_method"].value = std::string("none");
                factory().parameters()["ipopt.max_iter"].value = 2000;
                factory().parameters()["max-iterations"].value = 2000;
////                            factory().parameters()["ipopt.derivative_test"].value = std::string("first-order");
//
//                            factory().parameters()["ipopt.nlp_scaling_max_gradient"].value = 1e+4;
//                            factory().parameters()["ipopt.linear_scaling_on_demand"].value = std::string("yes");
                factory().parameters()["ipopt.print_level"].value = 12;
                factory().parameters()["ipopt.print_user_options"].value = std::string("yes");
                factory().parameters()["ipopt.print_info_string"].value = std::string("yes");
                factory().parameters()["ipopt.output_file"].value = std::string("/tmp/debug-ipopt.log");




                solver_t& solver = factory ();

//                                            std::cout << solver <<std::endl;

                solver_t::result_t res = solver.minimum ();
//                            std::cout<<res.which()<<std::endl;
                switch (res.which ())
                {
                    case solver_t::SOLVER_VALUE:
                    {
                        // Get the result.
                        ro::Result& result = boost::get<ro::Result> (res);

                        // Display the result.
//                                                                std::cout << "A solution has been found: "
//                                                                          << result << std::endl;
                        auto sol = result.x;
                        std::vector<double> final(sol.data(),sol.data() + sol.size());
                        solution = final;
                        //  std::cout << sol << std::endl;
//                        g->plot(init_guess_, num_params, 0.01, (const char *) "Init path");

//                        g->plot(final, num_params, 0.01, (const char *) "Final path");
//                        plt::show();
//                                        if ((solution[8]+solution[9]+solution[10])>1.5*(init_guess_[8]+init_guess_[9]+init_guess_[10]))
//                                            return 0;
                        success = true;
                        return 1;
                    }


                    case solver_t::SOLVER_ERROR:
                        return 0;
                    case solver_t::SOLVER_NO_SOLUTION:
                        return 0;
                }

            }
        };
    }
}


#endif
