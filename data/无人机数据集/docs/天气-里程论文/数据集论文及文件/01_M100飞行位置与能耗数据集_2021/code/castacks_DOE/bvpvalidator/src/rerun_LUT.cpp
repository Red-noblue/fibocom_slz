#include <stdio.h>
#include <math.h>
#include <iostream>
#include <stdlib.h>
#include <fstream>
#include "bvp_utils.h"
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"

#include "kite_bvp_solver/solver.h"
#include "kite_bvp_solver/kite_bvp_defs.h"
#include <boost/shared_ptr.hpp>
#include "kite_bvp_solver/guess.h"
#include <stack>
#include <ctime>
#include <ompl/geometric/PathGeometric.h>

#define debug false
#define num_points 100
using namespace ca;
namespace ob = ompl::base;
namespace og = ompl::geometric;
namespace kite = kite_bvp_solver;

struct solution{
    std::vector<double> q;
};

template <typename T>
std::ostream& operator<< (std::ostream& out, const std::vector<T>& v) {
    if ( !v.empty()  ) {
        out << '[';
        std::copy (v.begin(), v.end(), std::ostream_iterator<T>(out, ", "));
        out << "\b\b]";
    }
    return out;
}
void rerun_LUT() {
    // Define params
    kite::Params params;
    params.num_constraint_samples = 50;
    params.num_simpson_samples = num_points;
    params.bv_tol[0] = 1e-1;
    params.bv_tol[1] = 1e-1;
    params.bv_tol[2] = 1e-2;
    params.bv_tol[3] = 1e-2;
    params.bv_tol[4] = 1e-3;
    params.curv1_tol = 1e-4;
    params.precision = 2;
    params.constraint_tol = 1e-4;

    // Define constraints
    kite::Constraints constraints;
    constraints.max_curv = 1. / 20.;
    constraints.max_curv_rate = 1. / 20.;

    // Set up problem
    kite::BVProblem problem;
    problem.X0[0] = 0;
    problem.X0[1] = 0;
    problem.X0[2] = 0;
    problem.X0[3] = 0;

    problem.Xf[3] = 0;
    problem.v = 5;
    problem.vw_x = 0;
    problem.vw_y = 0;
    std::vector<solution> solutions;
    // other params
    double step_size = 0.01;

    std::string filename = "large_data.csv";
    boost::shared_ptr<kite::Solver<double, 4>> solver(new kite::Solver<double, 4>(params, constraints, filename));
    int count = 0, fail = 0;
    double wind[] = {0, 0, 0}, time=0;
    int lower_bound = -100, upper_bound = 100;
    for(int x = lower_bound; x <= upper_bound; x+= 5){
        for(int y = lower_bound; y <= upper_bound; y+= 5){
            for (int psi = 0; psi < 360; psi+=30) {
                if ((x >= -20 && x <= 20)||(y >= -20 && y <= 20))
                    continue;
                std::cout<<count<<std::endl;
                count++;
                problem.Xf[0] = x;
                problem.Xf[1] = y;
                problem.Xf[2] = psi*M_PI/180;
                if (debug)
                    std::cout<<"starting to solve"<<std::endl;
                // solve
                if (solver->multisolve(problem, wind)){
                    //std::cout<<solver->init_guess_<<std::endl;
                    std::cout<<"found new solution"<<std::endl;
                    solver->init->update(x, y, psi, solver->solution);
                    //std::cout<<solver->init->LUT[x][y][psi]<<std::endl;
                }
            }
        }
    }
    solver->init->write_data("/home/jay/new_lut.csv");
    //std::ofstream myfile("~/simulation_ws/src/bvpvalidator/src/new_lut.csv", std::ios_base::out);
    //std::copy(solutions.begin(), solutions.end(), std::ostream_iterator<std::vector<double>>(std::cout, "\n"));
}


int main(int argc, char **argv) {
    rerun_LUT();
}
