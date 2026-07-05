//
// Created by jay on 8/30/19.
//

#ifndef TROCHOID_UTILS_H
#define TROCHOID_UTILS_H
#include "ompl/geometric/PathGeometric.h"
#include "trochoids.h"
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "ompl/base/ScopedState.h"
#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"
#include "Wind_graph_data.h"
#include <ompl/geometric/PathGeometric.h>

namespace og = ompl::geometric;
namespace ob = ompl::base;

namespace ca{
    namespace trochoids{

        void getTrochoidPath(boost::shared_ptr<og::PathGeometric> path, std::shared_ptr<ca::planning_common::PathWaypoint> final,boost::shared_ptr<Wind_graph_data> wind);

        double getLength(const ob::State *s1, const ob::State *s2, double wind[]);

        bool getPath(const ob::State *s1, const ob::State *s2, std::shared_ptr<og::PathGeometric> path, double wind[]);
    }
}



#endif //BITSTAR3D_TROCHOID_UTILS_H
