
#include <stdio.h>
#include <math.h>
#include <iostream>
#include <stdlib.h>
#include "bvp_utils.h"
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"
#include <tuple>
#include "kite_bvp_solver/solver.h"
#include "kite_bvp_solver/kite_bvp_defs.h"
#include <boost/shared_ptr.hpp>
#include "kite_bvp_solver/guess.h"
#include <stack>
#include <ctime>
#include <ompl/geometric/PathGeometric.h>
#include <string>
#define eps_calc true
#define debug false
#define num_points 100

using namespace ca;
namespace ob = ompl::base;
namespace og = ompl::geometric;
namespace kite = kite_bvp_solver;

std::stack<clock_t> tictoc_stack;
void getPathfromcoeff(std::vector<double> q, double v, double z_init, double z_final, og::PathGeometric &final, double wind[3] ) {
    const int degree_ = 4;
    const double n = q.size();
    const double sf1 = q[n-3];
    const double sf2 = q[n-2];
    const double sf3 = q[n-1];
    const double sf = q[n-1] + q[n-2] + q[n-3];
    const double step_size = sf/num_points;
    unsigned num_path = int(sf / step_size) + 2;
    ob::ScopedState<ca::XYZPsiStateSpace> output(final.getSpaceInformation());
    ca::Polynomial<double, degree_> c1;
    ca::Polynomial<double, degree_> c2;
    ca::Polynomial<double, degree_> c3;
    c1[0] = 0.0;
    for (int i = 0; i < degree_; ++i) {
        c1[i + 1] = q[i];
        c3[i + 1] = q[i + degree_];
    }

    ca::Polynomial<double, degree_+1> psi1;
    ca::Polynomial<double, degree_+1> psi2;
    ca::Polynomial<double, degree_+1> psi3;
    c2[0] = c1.Evaluate(sf1);
    c3[0] = c2.Evaluate(sf2);
    // create heading polys
    psi1.SetToIntegral(c1, 0.0);
    psi2.SetToIntegral(c2, psi1.Evaluate(sf1));
    psi3.SetToIntegral(c3, psi2.Evaluate(sf2));
    std::vector<ca::Polynomial<double, degree_>> curv_polys = {c1, c2, c3};
    std::vector<ca::Polynomial<double, degree_ + 1>> psi_polys = {psi1, psi2,
                                                                  psi3};
    std::vector<double> breaks = {0, sf1, sf1 + sf2, sf};

    // evaluate solution to get path
    std::vector<double> path_x, path_y , path_z;
    double prev_x(0), prev_y(0), s(0), curv, psi, x, y, z, cos_psi, sin_psi, prev_cos, prev_sin;
    int curr_id(0);
    Eigen::Vector3d pos;


    path_x.push_back(0.0);
    path_y.push_back(0.0);
    path_z.push_back(z_init);
    pos << path_x.back(),path_y.back(),path_z.back();
    output->SetXYZ(pos);
    final.append(output.get());
    int count = 0;
    prev_cos = std::cos(psi_polys[curr_id].Evaluate(0));
    prev_sin = std::sin(psi_polys[curr_id].Evaluate(0));
//    while (s <= sf) {
    while (count<num_points){
        // check which poly we should evaluate
        if (s > breaks[curr_id + 1]) {
            // move on to the next poly
            ++curr_id;
        }

        psi = ca::math_utils::angular_math::WrapTo2Pi(0.0 +
                                                      psi_polys[curr_id].Evaluate(s - breaks[curr_id]));
        cos_psi = std::cos(psi);
        sin_psi = std::sin(psi);

        // perform integration using the trapezoidal rule (accurate enough?)
        x = path_x.back() + step_size * (cos_psi + prev_cos) / 2 +
            wind[0] * step_size / v;
        y = path_y.back() + step_size * (sin_psi + prev_sin) / 2 +
            wind[1] * step_size / v;
        z = ((z_final-z_init)*s/sf) + z_init; // linear integration 
        path_x.push_back(x);
        path_y.push_back(y);
        path_z.push_back(z);
        pos << path_x.back(),path_y.back(), path_z.back();
        output->SetXYZ(pos);
        output->SetPsi(psi);
        final.append(output.get());
        prev_cos = cos_psi;
        prev_sin = sin_psi;
        s += step_size;
//        std::cout<<s<<sf<<std::endl;
        count++;
    }


}
double getPathLengthfromcoeff(std::vector<double> q, double v,  double delta, double wind[3]){
    double length = 0.0;
    const int degree_ = 4;
    double z_init = 0.0;
    const double n = q.size();
    const double sf1 = q[n - 3];
    const double sf2 = q[n - 2];
    const double sf3 = q[n - 1];
    const double sf = q[n - 1] + q[n - 2] + q[n - 3];
    const double step_size = sf / num_points;
    unsigned num_path = int(sf / step_size) + 2;
    ca::Polynomial<double, degree_> c1;
    ca::Polynomial<double, degree_> c2;
    ca::Polynomial<double, degree_> c3;
    c1[0] = 0.0;
    for (int i = 0; i < degree_; ++i) {
        c1[i + 1] = q[i];
        c3[i + 1] = q[i + degree_];
    }

    ca::Polynomial<double, degree_ + 1> psi1;
    ca::Polynomial<double, degree_ + 1> psi2;
    ca::Polynomial<double, degree_ + 1> psi3;
    c2[0] = c1.Evaluate(sf1);
    c3[0] = c2.Evaluate(sf2);
    // create heading polys
    psi1.SetToIntegral(c1, 0.0);
    psi2.SetToIntegral(c2, psi1.Evaluate(sf1));
    psi3.SetToIntegral(c3, psi2.Evaluate(sf2));
    std::vector<ca::Polynomial<double, degree_>> curv_polys = {c1, c2, c3};
    std::vector<ca::Polynomial<double, degree_ + 1>> psi_polys = {psi1, psi2,
                                                                  psi3};
    std::vector<double> breaks = {0, sf1, sf1 + sf2, sf};

    // evaluate solution to get path
    std::vector<double> path_x, path_y, path_z;
    double prev_x(0), prev_y(0), s(0), curv, psi, x, y, z, cos_psi, sin_psi, prev_cos, prev_sin;
    int curr_id(0);
    Eigen::Vector3d pos;


    path_x.push_back(0.0);
    path_y.push_back(0.0);
    path_z.push_back(z_init);
    pos << path_x.back(), path_y.back(), path_z.back();
    prev_cos = std::cos(psi_polys[curr_id].Evaluate(0));
    prev_sin = std::sin(psi_polys[curr_id].Evaluate(0));
    while (s <= sf) {
        // check which poly we should evaluate
        if (s > breaks[curr_id + 1]) {
            // move on to the next poly
            ++curr_id;
        }

        //                curv = curv_polys[curr_id].Evaluate(s - breaks[curr_id]);
        psi = ca::math_utils::angular_math::WrapTo2Pi(0.0 +
                                                      psi_polys[curr_id].Evaluate(s - breaks[curr_id]));
        cos_psi = std::cos(psi);
        sin_psi = std::sin(psi);

        // perform integration using the trapezoidal rule (accurate enough?)
        x = path_x.back() + step_size * (cos_psi + prev_cos) / 2 +
            wind[0] * step_size / v;
        y = path_y.back() + step_size * (sin_psi + prev_sin) / 2 +
            wind[1] * step_size / v;
        z = ((delta - z_init) * s / sf) + z_init; // linear integration
        length += sqrt(pow(path_x.back()-x,2)+pow(path_y.back()-y,2)+pow(path_z.back()-z,2));

        path_x.push_back(x);
        path_y.push_back(y);
        path_z.push_back(z);

        prev_cos = cos_psi;
        prev_sin = sin_psi;
        s += step_size;
    }
    return length;
}


void tic(){
    tictoc_stack.push(clock());
}
double toc(){
    double time = ((double)clock() - tictoc_stack.top());
    tictoc_stack.pop();
    return time;
}
double eps_calculation(std::vector<double> q1, std::vector<double> q2, double wind[3], float x , float y, double v=5){
    ob::SpaceInformationPtr si_xyzpsi;
    ob::StateSpacePtr space(new XYZPsiStateSpace);
    si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
    og::PathGeometric path_1(si_xyzpsi), path_2(si_xyzpsi);
    double z_init = 0;
    getPathfromcoeff(q1, v, z_init, z_init, path_1, wind);
    getPathfromcoeff(q2, v, z_init, z_init, path_2, wind);
    double dist = std::numeric_limits<double>::min();
    assert(path_1.getStateCount() == path_2.getStateCount());
    if (debug){
        std::cout<<path_1.getStateCount()<<std::endl;
        std::cout<<"qs:"<<std::endl;
        for(int i=0;i<11;i++)
            std::cout<<q1[i]<<",";
        std::cout<<std::endl;
        for(int i=0;i<11;i++)
            std::cout<<q2[i]<<",";
        std::cout<<std::endl;
    }
//    std::cout<<path_1.getStateCount()<<std::endl;
//    std::cout<<path_2.getStateCount()<<std::endl;

    for(int i=0;i < path_1.getStateCount() ; i++){
//        std::cout<<i<<std::endl;
        dist = std::max(dist, si_xyzpsi->distance(path_1.getState(i),path_2.getState(i)));
    }
//    std::cout<<"b"<<std::endl;
    double b = si_xyzpsi->distance(path_1.getState(path_1.getStateCount()-1),path_2.getState(path_2.getStateCount()-1));

    return dist;
}

double sf_change(std::vector<double> q1, std::vector<double> q2, double wind[3], float x , float y, double v=5){
    ob::SpaceInformationPtr si_xyzpsi;
    ob::StateSpacePtr space(new XYZPsiStateSpace);
    si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
    og::PathGeometric path_1(si_xyzpsi), path_2(si_xyzpsi);
    double z_init = 0;
    auto d1 = getPathLengthfromcoeff(q1, v, z_init, wind);
    auto d2 = getPathLengthfromcoeff(q2, v, z_init, wind);
//    std::cout<<d1<<" "<<d2<<std::endl;
    double dist = abs(d1-d2)/d1;
    return dist;
}

std::tuple<bool, double, double>  multisolve(kite::BVProblem problem_,boost::shared_ptr<kite::Solver<double, 4>> solve, double wind[2]){
int trial = 0;
std::tuple<bool, double, double> time = std::make_tuple(false, 0, 0);
auto og_problem = problem_;

solve->init->reset();
while (trial < 1) {
auto t = clock();
//        std::cout<<trial<<std::endl;
solve->init->getInitBucket(problem_, wind);
solve->init_guess_ = solve->init->init_guess;
std::get<1>(time) = (double)(clock() - t)/CLOCKS_PER_SEC;
t = clock();
og_problem.vw_x = wind[0];
og_problem.vw_y = wind[1];
if (solve->solve(og_problem)) {
solve->init->reset();
std::get<2>(time) = (double)(clock() - t)/CLOCKS_PER_SEC;
std::get<0>(time)= true;
return time;
}
else
trial++;
//std::get<2>(time)+= toc()/CLOCKS_PER_SEC;
}
return time;

}

void write_data(std::vector<std::tuple<double, bool, double, double>> data, std::string filename){
    std::ofstream file(filename.c_str());
    for(auto row:data){
        file<<std::get<0>(row)<<",";
        file<<std::get<1>(row)<<",";
        file<<std::get<2>(row)<<",";
        file<<std::get<3>(row);
        file<<std::endl;
    }
    file.close();
}
void write_data(std::vector<std::pair<double,double>> data, std::string filename){
    std::ofstream file(filename.c_str());
    for(auto row:data){
        file<<row.first<<",";
        file<<row.second<<",";
//        file<<std::get<2>(row)<<",";
//        file<<std::get<3>(row);
        file<<std::endl;
    }
    file.close();
}
void test_bvp_solver() {
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

    // other params
    double step_size = 0.01;

    std::string filename = "large_data5.csv";
    boost::shared_ptr<kite::Solver<double, 4>> solver(new kite::Solver<double, 4>(params, constraints, filename));
    int count = 100;
    double wind[] = {1, 0, 0};
    float x, y, psi;
    double eps = 0;
    double sf = 0;
    double lower_bound = -100, upper_bound = 100;
    // storage for cool metrics
    std::vector<std::tuple<double, bool, double, double>> time_data_dump;
    std::vector<std::pair<double,double>> eps_data_dump;
    std::vector<std::pair<double,double>> sf_data_dump;

    for(int wind_ang = 0; wind_ang <= 360; wind_ang += 10){
        std::cout<<wind_ang<<std::endl;
        wind[0] = cos(wind_ang*M_PI/180);
        wind[1] = sin(wind_ang*M_PI/180);
        for (int i=0; i < count; i++) {
            x = lower_bound + static_cast <float> (rand()) /( static_cast <float> (RAND_MAX/(upper_bound-(lower_bound ))));
            y = lower_bound + static_cast <float> (rand()) /( static_cast <float> (RAND_MAX/(upper_bound-(lower_bound ))));
            psi = static_cast <float> (rand()) /( static_cast <float> (RAND_MAX/359) ) * M_PI/180;
            if (abs(x) <= 20 && abs(y) <= 20){
                i--;
                if(debug)
                    std::cout<<"Invalid point"<<std::endl;
                continue;
            }
            problem.Xf[0] = x;
            problem.Xf[1] = y;
            problem.Xf[2] = psi;
            if (debug)
                std::cout<<"starting to solve"<<std::endl;
            // solve
            auto soln = multisolve(problem, solver, wind);
            if (std::get<0>(soln)) {
//                std::cout << std::get<2>(soln) <<" "<<std::get<1>(soln) << std::endl;

                time_data_dump.push_back(std::tuple_cat(std::make_tuple(wind_ang*M_PI/180), soln));
            }
            if (debug){
                std::cout<<"calculating distance for "<<x<<", "<<y<<","<<psi<<std::endl;
                std::cout<<"seed is "<<problem.Xf[0]<<", "<<problem.Xf[1]<<","<<problem.Xf[2]<<std::endl;
            }
            // calculate eps
//            if (eps_calc){
            if (std::get<0>(soln)) {
////                auto dist = sqrt(pow(x - problem.Xf[0], 2) + pow(y - problem.Xf[1], 2));
////                if (dist != 0){
                eps = eps_calculation(solver->init_guess_, solver->solution, wind, x, y);
//                sf = sf_change(solver->init_guess_, solver->solution, wind, x, y);
//
                std::cout << eps <<" "<<sf<< std::endl;
                eps_data_dump.push_back(std::make_pair((wind_ang), eps));
//                sf_data_dump.push_back(std::make_pair((wind_ang), sf));
//
            }




//                if (debug)
//                        std::cout<<"total Dist "<< eps_calculation(solver->init_guess_, solver->solution, wind)/dist<<std::endl;
//            }
        }

    }

    write_data(eps_data_dump, std::string("/home/jay/simulation_ws/src/bvpvalidator/src/mag1test3eps.csv"));
//    write_data(sf_data_dump, std::string("/home/jay/simulation_ws/src/bvpvalidator/src/mag1test2sf.csv"));
//    write_data(time_data_dump, std::string("/home/jay/simulation_ws/src/bvpvalidator/src/mag1testtime.csv"));

}


int main(int argc, char **argv) {
    test_bvp_solver();
}
