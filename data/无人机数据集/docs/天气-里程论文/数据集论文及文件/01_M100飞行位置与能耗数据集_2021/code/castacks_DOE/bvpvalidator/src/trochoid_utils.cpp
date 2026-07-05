//
// Created by jay on 8/30/19.
//

#include "../include/bvpvalidator/trochoid_utils.h"
typedef std::vector<std::tuple<double,double,double> > Path;
namespace og = ompl::geometric;
namespace ob = ompl::base;

void ca::trochoids::getTrochoidPath(boost::shared_ptr<og::PathGeometric> path,
                                    std::shared_ptr<ca::planning_common::PathWaypoint> final,
                                    boost::shared_ptr<Wind_graph_data> wind) {
    ;


    std::cout<<path->getStateCount()<<std::endl;


    for (std::size_t i = 0; i<path->getStateCount() -1; i++){

        auto seg = std::make_shared<og::PathGeometric> (path->getSpaceInformation());
//        og::PathGeometric seg(path->getSpaceInformation());
//        seg->
        auto s1 = path->getState(i);
        auto s2 = path->getState(i + 1);

        auto *s1_pt = s1->as<ca::XYZPsiStateSpace::StateType>();
        auto *s2_pt = s2->as<ca::XYZPsiStateSpace::StateType>();
        double mean_z = (s1_pt->GetZ() + s2_pt->GetZ())/2.0;
        std::cout<<s1_pt->GetX()<<" "<< s1_pt->GetY()<< " "<<s1_pt->GetPsi()<<" "<< s2_pt->GetX()<< "  " << s2_pt->GetY()<<" "<<s2_pt->GetPsi()<<" "<<std::endl;

//        auto wind_cv = wind->query_2d_data(s1_pt->GetX(), s1_pt->GetY(), s2_pt->GetX(), s2_pt->GetY(), mean_z);
        double wind[3] = {0,0,0};
//        if (!(wind_cv[3] == 0 || isnan(wind_cv[0])))
//        {
//            wind[0] = wind_cv[0];
//            wind[1] = wind_cv[1];
//        }

        bool valid = getPath(s1,s2,seg,wind);

        for (std::size_t j = 0 ; j < seg->getStateCount(); j++) {
            final->AppendWaypoint(seg->getState(j));
        }

        seg->keepBefore(seg->getState(0));

    }
    std::cout<<final->NumberOfWaypoints()<<std::endl;




}

bool ca::trochoids::getPath(const ob::State *s1, const ob::State *s2, std::shared_ptr<og::PathGeometric> final, double *wind) {
    auto trochoid = std::make_shared<ca::trochoids::Trochoid> ();
    trochoid->problem.v = 5;
    trochoid->problem.wind = {wind[0],wind[1]};
    trochoid->problem.max_kappa = 1.0/4.0;
    Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
    Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();

    double psi1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    trochoid->problem.X0 = {vec1[0],vec1[1],psi1};
    trochoid->problem.Xf = {vec2[0],vec2[1],psi2};
    Path path = trochoid->getTrochoid();
    if (path.size()==0)
    {return false;}
    ob::ScopedState<ca::XYZPsiStateSpace> output(final->getSpaceInformation());
    Eigen::Vector3d pos;

    for(int i =0; i<path.size(); i++)
    {
        double x = std::get<0>(path[i]);
        double y = std::get<1>(path[i]);
        double psi = std::get<2>(path[i]);
        double z = vec1[2] + (((double)i)/(double)path.size())*(vec2[2]-vec1[2]);

        pos << x,y,z;
//        std::cout<<x<<" "<<y<<" "<<z<<std::endl;
        output->SetXYZ(pos);
        output->SetPsi(psi);
        final->append(output.get());

    }
    return true;

}
double ca::trochoids::getLength(const ob::State *s1, const ob::State *s2, double *wind) {
    auto trochoid = std::make_shared<ca::trochoids::Trochoid> ();
    trochoid->problem.v = 5;
    trochoid->problem.wind = {wind[0],wind[1]};
    trochoid->problem.max_kappa = 1.0/4.0;
    Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
    Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();

    double psi1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    trochoid->problem.X0 = {vec1[0],vec1[1],psi1};
    trochoid->problem.Xf = {vec2[0],vec2[1],psi2};
    Path path = trochoid->getTrochoid();
    double length(0.0);
//    std::cout<<path.size()<<std::endl;
    if (path.size()==0){
        return 0.0;
    }
    for(int i =0; i<path.size()-1; i++)
    {
        double x = std::get<0>(path[i]);
        double y = std::get<1>(path[i]);
        double psi = std::get<2>(path[i]);
        double z = vec1[2] + (((double)i)/(double)path.size())*(vec2[2]-vec1[2]);
        double x_ = std::get<0>(path[i+1]);
        double y_ = std::get<1>(path[i+1]);
        double z_ = vec1[2] + (((double)(i+1))/(double)path.size())*(vec2[2]-vec1[2]);

        length += sqrt(pow(x_-x,2)+pow(y_-y,2)+pow(z_-z,2));

    }
    return length;

}
