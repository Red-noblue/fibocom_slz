#include <stdio.h>
#include <math.h>
#include <iostream>
#include <stdlib.h>
#include "../../bvp_doe/include/kite_bvp_solver/solver.h"
#include <boost/shared_ptr.hpp>
#include <ctime>

using namespace ca;
namespace kite = kite_bvp_solver;
void test_bvp_solver(int x, int y, double wx,double wy) {
    // Define params
    kite::Params params;
    params.num_constraint_samples = 50;
    params.num_simpson_samples = 100;
    params.bv_tol[0] = 1e-1;
    params.bv_tol[1] = 1e-1;
    params.bv_tol[2] = 1e-2;
    params.bv_tol[3] = 1e-2;
    params.bv_tol[4] = 1e-3;
    params.curv1_tol = 1e-4;
    params.precision = 2;
    params.constraint_tol = 1e-4;

    // Define consraints
    kite::Constraints constraints;
    constraints.max_curv = 1./20.;
    constraints.max_curv_rate = 1./20.;

    // Set up problem
    // 85, 30,4.71239
    kite::BVProblem problem;
    problem.X0[0] = 0;
    problem.X0[1] = 0;
    problem.X0[2] = 0;
    problem.X0[3] = 0;
    problem.Xf[0] = x;
    problem.Xf[1] = y;
    problem.Xf[2] = 0;// - 0.1745;
    problem.Xf[3] = 0;
    problem.v = 5;
    problem.vw_x = wx;
    problem.vw_y = wy;

    // other params
    double step_size = 0.01;

    std::string filename = "large_data5.csv";



    boost::shared_ptr<kite::Solver<double,4>>solver (new kite::Solver<double,4> (params, constraints, filename));
//
    double wind[] = {problem.vw_x,problem.vw_y};
    solver->init->getInitBucket(problem, wind);
    solver->init_guess_ = solver->init->init_guess;
//    for(auto i:solver->init_guess_){
//        std::cout<<i<<",";
//    }
//    std::cout<<std::endl;
    auto time = clock();
    if (solver->solve(problem)) {
        std::cout << "Success" << std::endl;
        auto q = solver->solution;
//        for(auto i:q){
//            std::cout<<i<<",";
//        }
//        std::cout<<std::endl;
    }
    else{
        std::cout<<"failed";
    }
    std::cout<< (double)(clock()-time)/CLOCKS_PER_SEC<<std::endl;



}

int main(int argc, char **argv) {
    while (1) {
        int x = 100*(2.0 * (rand() / (double) RAND_MAX) - 1.0);
        int y = 100*(2.0 * (rand() / (double) RAND_MAX) - 1.0);
        double wx = 2*(2.0 * (rand() / (double) RAND_MAX) - 1.0);
        double wy = 2*(2.0 * (rand() / (double) RAND_MAX) - 1.0);
        std::cout<<x<<" "<<y<<" "<<wx<<" "<<wy<<std::endl;
        test_bvp_solver(x,y,wx,wy);
    }
}
