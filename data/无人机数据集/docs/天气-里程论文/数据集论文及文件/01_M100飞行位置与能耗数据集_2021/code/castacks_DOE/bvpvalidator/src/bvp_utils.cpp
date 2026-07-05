//
// Created by jay on 6/18/19.
//

#include "../include/bvpvalidator/bvp_utils.h"
#include "geom_cast/point_cast.hpp"

namespace ob = ompl::base;
namespace og = ompl::geometric;

void bvp_utils::makeTanget(boost::shared_ptr<og::PathGeometric> path) {
    for (std::size_t i = 0; i<path->getStateCount() -1; i++) {
        auto s1 = path->getState(i);
        auto s2 = path->getState(i + 1);
        Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
        Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
        double psi1 = atan2(vec2.y() - vec1.y(), vec2.x() - vec1.x());
        path->getState(i)->as<ca::XYZPsiStateSpace::StateType>()->SetPsi(psi1);

    }

}

void bvp_utils::savePath(std::shared_ptr<pc::PathWaypoint> final, std::string filename) {
    filename  = "/home/jay/simulation_ws/src/bitstarbvp/"+ filename + ".csv";
    std::ofstream file(filename.c_str());
    for (std::size_t i = 0; i<final->NumberOfWaypoints(); i++){
        auto s1 = final->GetWaypoint(i);
        Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
        double psi = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
        file<<vec1(0)<<",";
        file<<vec1(1)<<",";
        file<<vec1(2)<<",";
        file<<psi;
        file<<std::endl;

    }
    file.close();


}
bool bvp_utils::getBVPPath(ompl::base::SpaceInformationPtr si, boost::shared_ptr<og::PathGeometric> path, std::shared_ptr<pc::PathWaypoint> final,boost::shared_ptr<Wind_graph_data> wind_query,bool opt) {
    std::string filename = "large_data5.csv";
    auto init = boost::shared_ptr<ca::kite_bvp_solver::Init>(new ca::kite_bvp_solver::Init(filename));
    ca::kite_bvp_solver::Params params;
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
    ca::kite_bvp_solver::Constraints constraints;
    constraints.max_curv = 1. / 20.;
    constraints.max_curv_rate = 1. / 20.;



    boost::shared_ptr<ca::kite_bvp_solver::Solver<double, 4>> solver(new ca::kite_bvp_solver::Solver<double, 4>(params, constraints, filename));

    double v = 5.0;
    double z_init, z_final;
    std::cout<<path->getStateCount()<<std::endl;
    auto numberprobs = path->getStateCount();
    int success = 0;

    for (std::size_t i = 0; i<path->getStateCount() -1; i++){

        og::PathGeometric seg(final->getSpaceInformation());
        auto s1 = path->getState(i);
        auto s2 = path->getState(i + 1);
        z_init = s1->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
        z_final = s2->as<ca::XYZPsiStateSpace::StateType>()->GetZ();

//        std::cout << s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi()<<std::endl;
        ca::kite_bvp_solver::BVProblem problem = TfToOrigin(s1,s2);
        problem.v = 5;



        std::vector<double> q;

//        init->reset();
        auto *s1_pt = s1->as<ca::XYZPsiStateSpace::StateType>();
        auto *s2_pt = s2->as<ca::XYZPsiStateSpace::StateType>();
        double mean_z = (s1_pt->GetZ() + s2_pt->GetZ())/2.0;
//        std::cout<<s1_pt->GetX()<<", "<<s1_pt->GetY()<<std::endl;
//        std::cout<<s2_pt->GetX()<<", "<<s2_pt->GetY()<<std::endl;
//
//        std::cout<<"mean_z"<<mean_z<<std::endl;
        auto wind_cv = wind_query->query_2d_data(s1_pt->GetX(), s1_pt->GetY(), s2_pt->GetX(), s2_pt->GetY(), mean_z);
        double wind[3] = {0,0,0};
        problem.vw_x = 0;
        problem.vw_y = 0;
        if (!(wind_cv[3] == 0 || isnan(wind_cv[0])))
        {
            wind[0] = (wind_cv[0]/fabs(wind_cv[0]))*std::min(3.0,wind_cv[0]);
            wind[1] = (wind_cv[1]/fabs(wind_cv[1]))*std::min(3.0,wind_cv[1]);
            problem.vw_x = wind[0];
            problem.vw_y = wind[1];
        }
        std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2]*180/M_PI << " " << wind[0]<<" "<<wind[1]<<std::endl;

        if (!opt) {
        init->reset();
//        double wind[3] = {0,0,0};
        init->getInitBucket(problem, wind);
        q = init->init_guess;
//        std::cout<<init->x_seed<<" "<<init->y_seed<<std::endl;
        init->reset();

        }
        else {
            init->reset();
            init->getInitBucket(problem, wind);
            q = init->init_guess;
            init->reset();

            solver->init->reset();

            for (int i =0;i<10;i++) {
                std::cout<<i<<std::endl;
                solver->init->getInitWind(problem, wind);
                solver->init_guess_ = solver->init->init_guess;
                auto q_ = solver->init->init_guess;
                    if (isvalid(si, s1, q_, problem.v, z_final - z_init, wind, 500)){
                    if(solver->solve(problem))
                    {
                        q_ = solver->solution;
                        if (isvalid(si, s1, q_, problem.v, z_final - z_init, wind, 500)) {
                            success++;
                            q = q_;
                            break;
                        }
                    }
                }
//                std::cout << "Colllsion" << isvalid(si, s1, q, problem.v, z_final - z_init, wind, 100) << std::endl;
            }
            solver->init->reset();


//            solver->multisolve(problem, wind);
//
//
//            if (solver->success)
//            {
//                success++;
//            }
//            q = solver->solution;
        }

//        std::cout<<q[8]+q[9]+q[10]<<" "<<final->getSpaceInformation()->distance(s1,s2)<<std::endl;
//        wind[1] = 1.0;

        bvp_utils::getPathfromcoeff(q, v, 0,  z_final - z_init, seg, wind, 100);

        for (std::size_t j = 0 ; j < seg.getStateCount(); j++) {
            final->AppendWaypoint(bvp_utils::TftoPath(s1, seg.getState(j)));
        }

        seg.keepBefore(seg.getState(0));

    }
//    std::cout<<final->NumberOfWaypoints()<<std::endl;
    std::cout<<success<<" "<<numberprobs<<std::endl;

    return success==numberprobs;




}



ob::State * bvp_utils::TftoPath( const ob::State *base,  ob::State *target) {
    //base->as<ca::XYZPsiStateSpace::StateType>()->SetZ(0.0);

    tf::Transform transform = ca::xyzpsi_state_space_utils::GetTF(base);
    tf::Transform pose = ca::xyzpsi_state_space_utils::GetTF(target);

    pose = transform*pose;

    //target->as<ca::XYZPsiStateSpace::StateType>()->SetXYZ( ca::point_cast<Eigen::Vector3d>(pose.getOrigin()) );
    ob::SpaceInformationPtr si_xyzpsi;
    ob::StateSpacePtr space(new ca::XYZPsiStateSpace);
    si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
    ob::State* state  = si_xyzpsi->allocState();
    auto tmp_state = state->as<ca::XYZPsiStateSpace::StateType>();
    tmp_state->SetXYZ(ca::point_cast<Eigen::Vector3d> (pose.getOrigin()));
    tmp_state->SetPsi(tf::getYaw(pose.getRotation()));

    //target->as<ca::XYZPsiStateSpace::StateType>()->SetPsi(tf::getYaw(pose.getRotation()));
    return state;

}

ca::kite_bvp_solver::BVProblem bvp_utils::TfToOrigin(const ob::State *s1, const ob::State *s2) {

    tf::Transform transform = ca::xyzpsi_state_space_utils::GetTF(s1);
    tf::Transform pose = ca::xyzpsi_state_space_utils::GetTF(s2);
    transform = transform.inverse();
    pose = transform*pose;

    ca::kite_bvp_solver::BVProblem problem;
    problem.X0 = {0.0,0.0,0.0,0.0};
    problem.Xf[3] = 0.0;
    problem.Xf[0] = pose.getOrigin().x();//goal[0];
    problem.Xf[1] = pose.getOrigin().y();
//    std::cout<< s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi()*180/M_PI<< ' '<< s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi()*180/M_PI<<' ' <<tf::getYaw(pose.getRotation())*180/M_PI<<std::endl;
    problem.Xf[2] = ca::math_utils::angular_math::WrapTo2Pi(tf::getYaw(pose.getRotation()));//s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();

    return problem;


}


void bvp_utils::getPathfromcoeff(std::vector<double> q, double v, double z_init, double z_final, og::PathGeometric &final, double wind[3], int num_points) {
    const int degree_ = 4;
    const double n = q.size();
    const double sf1 = q[n - 3];
    const double sf2 = q[n - 2];
    const double sf3 = q[n - 1];
    const double sf = q[n - 1] + q[n - 2] + q[n - 3];
    const double step_size = sf / num_points;
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
    output->SetXYZ(pos);
    final.append(output.get());
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
                (wind[0] * step_size) / v;
        y = path_y.back() + step_size * (sin_psi + prev_sin) / 2 +
                (wind[1] * step_size) / v;
        z = ((z_final - z_init) * s / sf) + z_init; // linear integration
        path_x.push_back(x);
        path_y.push_back(y);
        path_z.push_back(z);
        pos << path_x.back(), path_y.back(), path_z.back();
        output->SetXYZ(pos);
        output->SetPsi(psi);
        final.append(output.get());
//        std::cout<<final.getStateCount()<<std::endl;
//                path(path_id, 2) = psi;
//                path(path_id, 3) = curv;
        prev_cos = cos_psi;
        prev_sin = sin_psi;
        s += step_size;
    }
}
double  bvp_utils::getPathLengthfromcoeff(std::vector<double> q, double v,  double delta, double wind[3], int num_points){
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

bool bvp_utils::isvalid(ompl::base::SpaceInformationPtr si_,ob::State *s1,std::vector<double> q, double v, double z_del, double *wind, int num_points) {
//    ob::SpaceInformationPtr si_xyzpsi;
//    ob::StateSpacePtr space(new XYZPsiStateSpace);
//    si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
    og::PathGeometric final(si_);
    bvp_utils::getPathfromcoeff(q, v, 0, z_del, final, wind, 100);
    bool valid = true;
    for(int i=1;i < final.getStateCount() -1; i+=5){
        auto pt =  bvp_utils::TftoPath(s1, final.getState(i));
        if(!si_->satisfiesBounds(pt)){
            valid = false;
            break;
        }

        if (!si_->isValid(pt)){
                //std::cout<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetX()<<", "<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetY()<<std::endl;
                si_->freeState(pt);
                valid =  false;
                break;
            }
        si_->freeState(pt);
    }
    return valid;

}

