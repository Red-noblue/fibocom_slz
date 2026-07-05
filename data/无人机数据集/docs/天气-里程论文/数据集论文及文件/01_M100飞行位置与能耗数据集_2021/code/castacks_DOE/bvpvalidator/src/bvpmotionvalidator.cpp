//
// Created by jay on 7/28/19.
//

#include "../include/bvpvalidator/bvpmotionvalidator.h"
#include "../include/bvpvalidator/bvp_utils.h"
//#include "../include/bvpvalidator/bvpobjective.h"
//#define scale_factor 400 // scaling factor from x-y to actual meters
//const double min_x = -7.55109; // extents for the data (found using min and max of column)
//const double min_y = -3.25;
//const double max_x = 4.00121;
//const double max_y = 3.25;
//const double inc_x = 0.012409;
//const double inc_y = 0.0125;

namespace ob = ompl::base;

namespace ca {

    void BVPMotionValidator::defaultSettings(void)
    {
        stateSpace = si_->getStateSpace().get();
        //        stateSpace = dynamic_cast<XYZPsiStateSpace*>(si_->getStateSpace().get());
        if (stateSpace == nullptr)
            throw ompl::Exception("No state space for motion validator");
        std::string filename = "large_data5.csv";

        init = boost::shared_ptr<ca::kite_bvp_solver::Init>(new ca::kite_bvp_solver::Init(filename));
        //wind data
//        wind_query = boost::shared_ptr<Wind_graph_data>(new Wind_graph_data(min_x, min_y, max_x, max_y, inc_x, inc_y, scale_factor));
//        for (int i = 20; i <= 100; i += 5) { // insert data
//            wind_query->cv2_layer((const std::string) "/home/jay/wind_processed/f" + std::to_string(i) + ".csv", i);
//            std::cout<<"Loading wind for "<<i<<std::endl;
//        }
    }

    bool BVPMotionValidator::checkMotion(const ob::State *s1, const ob::State *s2) const {

        if (!si_->isValid(s2))
            return false;

        return (pathValidator(s1,s2) && zValidator(s1,s2));
    }
    bool BVPMotionValidator::checkMotion(const ob::State *s1, const ob::State *s2,
            std::pair<ob::State *, double> &lastValid) const
    {
        /* assume motion starts in a valid configuration so s1 is valid */

        bool result = true;
        int nd = stateSpace->validSegmentCount(s1, s2);

        if (nd > 1)
        {
            /* temporary storage for the checked state */
            ob::State *test = si_->allocState();

            for (int j = 1; j < nd; ++j)
            {
                stateSpace->interpolate(s1, s2, (double)j / (double)nd, test);
                if (!si_->isValid(test))
                {
                    lastValid.second = (double)(j - 1) / (double)nd;
                    if (lastValid.first != nullptr)
                        stateSpace->interpolate(s1, s2, lastValid.second, lastValid.first);
                    result = false;
                    break;
                }
            }
            si_->freeState(test);
        }

        if (result)
            if (!si_->isValid(s2))
            {
                lastValid.second = (double)(nd - 1) / (double)nd;
                if (lastValid.first != nullptr)
                    stateSpace->interpolate(s1, s2, lastValid.second, lastValid.first);
                result = false;
            }

        if (result)
            valid_++;
        else
            invalid_++;

        return result;
    }


    void BVPMotionValidator::setGlideslope(double slope) {
        guideslope = slope;
        ROS_INFO("Setting Glideslope");
    }

    bool BVPMotionValidator::zValidator(const ob::State *state1, const ob::State *state2) const {
        auto *s1 = static_cast<const XYZPsiStateSpace::StateType*>(state1);
        auto *s2 = static_cast<const XYZPsiStateSpace::StateType*>(state2);
        //        if (abs(s2->GetZ() - s1->GetZ() )>= 20.0) {
        //            return false;
        //        }

        double dist = stateSpace->distance(state1, state2);
        //        ROS_INFO("Dist %f",dist);
        double slope = atan2(abs(s1->GetZ() - s2->GetZ()) ,dist);
        if (abs(slope) > 0.5235) {
            return false;
        } else {
            //ROS_INFO("%f",slope);
            return true;
        }
    }

    bool BVPMotionValidator::pathValidator(const ob::State *s1, const ob::State *s2) const {
        /* assume motion starts in a valid configuration so s1 is valid */



        if (!si_->isValid(s2)) {
            invalid_++;
            return false;
        }
        if(!si_->satisfiesBounds(s2)){
            return false;
        }

        double z1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
        double z2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetZ();


        ca::kite_bvp_solver::BVProblem problem = bvp_utils::TfToOrigin(s1, s2);
//                    std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2] << std::endl;
//        Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//        Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//        double psi1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
//        double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
////    double q0[] = { vec1[0],vec1[1],psi1 };
////    double q1[] = { vec2[0],vec2[1],psi2 };
//
//        double q0[] = {0,0,0};
//        double q1[] = {problem.Xf[0],problem.Xf[1],problem.Xf[2]};
//
//        double turning_radius = 20.0;
//        DubinsPath path;
//        dubins_shortest_path( &path, q0, q1, turning_radius);
//        double s_dub = ca::kite_bvp_solver::dubins_path_length(&path);
////    double sh = si_->heuristicDistance(s1, s2);// sqrt(pow(,2)+ pow(z,2));
//        double sh = s_dub;
//        if (sh> s)
//        {    std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2] << std::endl;
//
//            std::cout<<"fail"<<sh- s<<std::endl;}
        if ((abs(problem.Xf[0]) < 20.0 && abs(problem.Xf[1]) < 20.0)){

//        if (abs(problem.Xf[0]) > 100.0 || abs(problem.Xf[1]) > 100.0 || (abs(problem.Xf[0]) < 20.0 && abs(problem.Xf[1]) < 20.0)){
//            //            std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2] << std::endl;
            return false;
        }
        //            std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2] << std::endl;
        auto *s1_pt = s1->as<ca::XYZPsiStateSpace::StateType>();
        auto *s2_pt = s2->as<ca::XYZPsiStateSpace::StateType>();
        double mean_z = (s1_pt->GetZ() + s2_pt->GetZ())/2.0;
//        std::cout<<s1_pt->GetX()<<", "<<s1_pt->GetY()<<std::endl;
//        std::cout<<s2_pt->GetX()<<", "<<s2_pt->GetY()<<std::endl;
//
//        std::cout<<"mean_z"<<mean_z<<std::endl;
        auto wind_cv = wind_query->query_2d_data(s1_pt->GetX(), s1_pt->GetY(), s2_pt->GetX(), s2_pt->GetY(), mean_z);
        double wind[3] = {0,0,0};
        if (!(wind_cv[3] == 0 || isnan(wind_cv[0])))
        {
            wind[0] = (wind_cv[0]/fabs(wind_cv[0]))*std::min(3.0,wind_cv[0]);
            wind[1] = (wind_cv[1]/fabs(wind_cv[1]))*std::min(3.0,wind_cv[1]);
        }
//        std::cout<<wind[0]<<" "<<wind[1]<<" "<<wind[2]<<std::endl;




        init->reset();
        init->getInitBucket(problem, wind);
        std::vector<double> q = init->init_guess;
//        std::cout<<init->x_seed<<" "<<init->y_seed<<std::endl;
        init->reset();
        double v = 5;
//        Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//        Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//        double psi1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
//        double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
//        double q0[] = { 0,0,0};
//        double q1[] = { problem.Xf[0],problem.Xf[1],problem.Xf[2]};
//        double turning_radius = 20.0;
//        ca::kite_bvp_solver::DubinsPath path;
//        ca::kite_bvp_solver::dubins_shortest_path( &path, q0, q1, turning_radius);
//        double s_dub = ca::kite_bvp_solver::dubins_path_length(&path);
//        double s = bvp_utils::getPathLengthfromcoeff(q,v,z2-z1,wind,100);
////            double s_h = ca::trochoids::getLength(s1,s2,wind);
//        double s_h = si_->heuristicDistance(s1,s2);
////        s_dub = sqrt(pow(s_dub,2)+ pow(z2-z1,2));
//        if (s_h>s)
//        {
////            std::cout<<"Hfailed"<<std::endl;
//            return false;
//        }




        auto *state1 = static_cast<const XYZPsiStateSpace::StateType*>(s1);
        auto *state2 = static_cast<const XYZPsiStateSpace::StateType*>(s2);
        bool valid = true;
//        int nd = stateSpace->validSegmentCount(s1, s2);
        ob::SpaceInformationPtr si_xyzpsi;
        ob::StateSpacePtr space(new XYZPsiStateSpace);
        si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
        og::PathGeometric final(si_xyzpsi);
        bvp_utils::getPathfromcoeff(q, 5, 0, state2->GetZ() - state1->GetZ(), final, wind, 100);
        double xf = final.getState(final.getStateCount() - 1)->as<ca::XYZPsiStateSpace::StateType>()->GetX();
        double yf = final.getState(final.getStateCount() - 1)->as<ca::XYZPsiStateSpace::StateType>()->GetY();
        double dist = sqrt(pow(xf - problem.Xf[0], 2) + pow(yf - problem.Xf[1], 2));
//        std::cout<<dist<<std::endl;
//        std::cout<<si_->distance(s2,bvp_utils::TftoPath(s1,final.getState(final.getStateCount()-1)))<<std::endl;
      if (dist > 10){
//          return false;
      }
//        std::cout<<dist<<std::endl;
        for(int i=1;i < final.getStateCount() -1; i+=5){
            auto pt =  bvp_utils::TftoPath(s1, final.getState(i));
            //std::cout<<pt->GetX()<<", "<<pt->GetY()<<std::endl;
            //auto pt2 =  bvp_utils::TftoPath(s1, final.getState(i))->as<ca::XYZPsiStateSpace::StateType>();
            //std::cout<<pt2->GetX()<<", "<<pt2->GetY()<<std::endl;
            if(!si_->satisfiesBounds(pt)){
                valid = false;
                break;
            }


//            if (!si_->isValid(pt)){
//                //std::cout<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetX()<<", "<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetY()<<std::endl;
//                si_xyzpsi->freeState(pt);
//                valid =  false;
//                break;
//            }
            if (!clearanceValidator(pt,5.0)){
                //std::cout<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetX()<<", "<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetY()<<std::endl;
                si_xyzpsi->freeState(pt);
                valid =  false;
                break;
            }
//            if (!si_->getStateValidityChecker()->clearance(pt)){
//                //std::cout<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetX()<<", "<<pt->as<ca::XYZPsiStateSpace::StateType>()->GetY()<<std::endl;
//                si_xyzpsi->freeState(pt);
//                valid =  false;
//                break;
//            }
            si_xyzpsi->freeState(pt);
        }
//        std::cout << problem.Xf[0] << ' ' << problem.Xf[1] << ' ' << problem.Xf[2] << std::endl;

        //std::cout<<valid<<std::endl;
        //ob::State* state  = si_xyzpsi->allocState();
        //auto *tmp_state = static_cast<XYZPsiStateSpace::StateType*>(state);
        //tmp_state->SetX(25.0);
        //tmp_state->SetY(30.0);
        //tmp_state->SetZ(10.0);
        //tmp_state->SetPsi(0);
        //std::cout<<si_->isValid(state)<<std::endl;
        //si_xyzpsi->freeState(state);
//        if (valid)
//            std::cout<<valid<<std::endl;
        return valid;

    }
    bool BVPMotionValidator::clearanceValidator(const ompl::base::State *s1, double dist) const{
        if (!si_->isValid(s1)){
            return false;
        }
        ob::ScopedState<ca::XYZPsiStateSpace> output(si_->getStateSpace());
        ob::copyStateData(si_->getStateSpace(),output.get(),si_->getStateSpace(),s1);
        output->SetX(output->GetX()+dist);
        if(si_->satisfiesBounds(output.get())) {
            if (!si_->isValid(output.get())) {
                return false;
            }
        }
        ob::copyStateData(si_->getStateSpace(),output.get(),si_->getStateSpace(),s1);
        output->SetX(output->GetX()-dist);

        if(si_->satisfiesBounds(output.get())) {
            if (!si_->isValid(output.get())) {
                return false;
            }
        }
        ob::copyStateData(si_->getStateSpace(),output.get(),si_->getStateSpace(),s1);
        output->SetY(output->GetY()+dist);
        if(si_->satisfiesBounds(output.get())) {
            if (!si_->isValid(output.get())) {
                return false;
            }
        }
        ob::copyStateData(si_->getStateSpace(),output.get(),si_->getStateSpace(),s1);
        output->SetY(output->GetY()-dist);
        if(si_->satisfiesBounds(output.get())) {
            if (!si_->isValid(output.get())) {
                return false;
            }
        }
        return true;


    }
}
