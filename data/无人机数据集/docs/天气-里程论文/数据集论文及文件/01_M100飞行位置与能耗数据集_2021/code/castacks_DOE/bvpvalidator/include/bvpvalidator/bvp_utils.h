//
// Created by jay on 6/18/19.
//

#ifndef BVPVALIDATOR_INCLUDE_BVP_UTILS_H
#define BVPVALIDATOR_INCLUDE_BVP_UTILS_H


#include <planning_common/paths/path_waypoint.h>
#include <ompl/geometric/PathGeometric.h>
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "math_utils/math_utils.h"
#include "../../polynomials/include/polynomials/polynomials.h"
#include "ompl/base/ScopedState.h"
#include "../../bvp_doe/include/kite_bvp_solver/guess.h"
#include "../../bvp_doe/include/kite_bvp_solver/kite_bvp_defs.h"
#include "../../bvp_doe/include/kite_bvp_solver/solver.h"

#include "tf/tf.h"
#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"
#include "Wind_graph_data.h"



namespace og = ompl::geometric;
namespace ob = ompl::base;


namespace pc = ca::planning_common;

namespace bvp_utils {
    void getPathfromcoeff(std::vector<double> q, double v, double z_init, double z_final, og::PathGeometric &final, double wind[3], int num_points);

    double getPathLengthfromcoeff(std::vector<double> q, double v, double z_del, double wind[3], int num_points);

    void savePath(std::shared_ptr<pc::PathWaypoint> final, std::string path);

    bool getBVPPath(ompl::base::SpaceInformationPtr si,boost::shared_ptr<og::PathGeometric> path, std::shared_ptr<pc::PathWaypoint> final,boost::shared_ptr<Wind_graph_data> wind, bool);

    bool isvalid(ompl::base::SpaceInformationPtr si_,ob::State *s1, std::vector<double> q, double v, double z_del, double wind[3], int num_points );

    ca::kite_bvp_solver::BVProblem TfToOrigin(const ob::State *s1, const ob::State *s2);

    ob::State * TftoPath(const ob::State *base,  ob::State *target) ;

    void makeTanget(boost::shared_ptr<og::PathGeometric> path);
};


#endif //BITSTAR3D_BVP_UTILS_H

