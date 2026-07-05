//
// Created by jay on 7/28/19.
//

#ifndef BVPVALIDATOR_INCLUDE_BVPMOTIONVALIDATOR_H
#define BVPVALIDATOR_INCLUDE_BVPMOTIONVALIDATOR_H

#include "ompl/base/MotionValidator.h"
#include "ompl/base/SpaceInformation.h"
#include <ros/console.h>
#include <queue>
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "ompl/tools/config/MagicConstants.h"
#include "../../bvp_doe/include/kite_bvp_solver/guess.h"
//#include "../../wind_query_ros/include/Wind_graph_data.h"
#include "Wind_graph_data.h"
#include "bvpobjective.h"


namespace ca {
    class BVPMotionValidator : public ompl::base::MotionValidator{


    public:
        boost::shared_ptr<kite_bvp_solver::Init> init;
        boost::shared_ptr<Wind_graph_data> wind_query; 

        BVPMotionValidator(ompl::base::SpaceInformation* si,boost::shared_ptr<Wind_graph_data> wind) : ompl::base::MotionValidator(si) {
            std::cout <<"Setting wind in validator"<<std::endl;
            wind_query = wind;
            defaultSettings();
        }
        BVPMotionValidator(const ompl::base::SpaceInformationPtr &si, boost::shared_ptr<Wind_graph_data> wind) : ompl::base::MotionValidator(si)
        {
            std::cout <<"Setting wind in validator"<<std::endl;
            wind_query = wind;
            defaultSettings();
        }


        ~BVPMotionValidator(){}

        bool checkMotion(const ompl::base::State *s1, const ompl::base::State *s2) const;

        bool checkMotion(const ompl::base::State *s1, const ompl::base::State *s2,
                         std::pair<ompl::base::State *, double> &lastValid) const;

        bool zValidator(const ompl::base::State *s1, const ompl::base::State *s2) const;

        bool pathValidator(const ompl::base::State *s1, const ompl::base::State *s2) const;

        bool clearanceValidator(const ompl::base::State *s1, double dist) const;

        void setGlideslope(double slope);

    private:
        ompl::base::StateSpace *stateSpace;

        double guideslope;

        void defaultSettings(void);

    };

}

#endif
