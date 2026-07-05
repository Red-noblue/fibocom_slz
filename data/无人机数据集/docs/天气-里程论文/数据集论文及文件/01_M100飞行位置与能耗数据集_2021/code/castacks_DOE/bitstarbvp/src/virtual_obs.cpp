//
// Created by jay on 8/19/19.
//

#include <iostream>
#include <ros/ros.h>
#include <tf/transform_broadcaster.h>
#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "ompl/base/SpaceInformation.h"
#include "ompl/base/ScopedState.h"
#include "planning_common/utils/visualization_utils.h"
#include <ompl/geometric/planners/bitstar/BITstar.h>
#include <ompl/geometric/planners/rrt/RRTstar.h>

#include "ompl/base/objectives/PathLengthOptimizationObjective.h"
#include <Eigen/Dense>
#include "../../bvpvalidator/include/bvpvalidator/bvpmotionvalidator.h"
#include "../../bvpvalidator/include/bvpvalidator/bvp_utils.h"
#include "../../bvpvalidator/include/bvpvalidator/bvpobjective.h"

#include "shapes/shapes.h"


namespace ob = ompl::base;
namespace og = ompl::geometric;
namespace xsu = ca::xyzpsi_state_space_utils;
namespace pc = ca::planning_common;
namespace vu = pc::visualization_utils;
ros::Publisher pub_path_bit;
ros::Publisher pub_path_bvp;
ros::Publisher pub_obstacles_marker_array;
ros::Publisher pub_graph_marker;
//namespace ca {
class planner {



public:

    ob::SpaceInformationPtr si_xyzpsi = xsu::GetStandardXYZPsiSpacePtr();



    planner()
    {
        ROS_INFO("Initialized");


    }
    ~planner()
    {}
    bool plan(const ob::State *start_ptr,const ob::State *goal_ptr)
    {
        ompl::base::RealVectorBounds bounds(3);
        ob::StateSpacePtr space(new ca::XYZPsiStateSpace);

        bounds.setLow(0, -70);
//        bounds.setLow(0, -50.0);

        bounds.setLow(1, -10);
        bounds.setLow(2, 20);

        bounds.setHigh(0, 70);
//        bounds.setHigh(0, 150.0);

        bounds.setHigh(1, 1000);
        bounds.setHigh(2, 100.0); //FAA limits
        space->as<ca::XYZPsiStateSpace>()->SetBounds(bounds);
        si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));


        ca::ShapeSet obstacle_set;
        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(0, 40, 20, 10, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(-50, 70, 20, 10, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(50, 70, 20, 10, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(0, 100, 20, 10, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper

//        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(-15, 50, 3, 100, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
//        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(15, 25, 3, 50, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
//        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(45, 50, 3, 100, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper
//        obstacle_set.AddShape(boost::shared_ptr<ca::Shape>(new ca::Cuboid(15, 100, 60, 3, 0, 100))); // x_com,  y_com,  x_size,  y_size,  z_lower,  z_upper


        // Tell the planner how to collision check by creating a function handle that takes a state as input and returns feasible or not
        boost::function<bool(const ob::State*)> valid_fn = [&](const ob::State* s) {
            Eigen::Vector3d pos = pc::workspace_utils::GetTranslationVector3d(si_xyzpsi, s); // Extract 3d workspace information (would work for non R3 spaces too!)
            return !obstacle_set.InShapeSet(pos);
        };
        si_xyzpsi->setStateValidityChecker(valid_fn);
        ob::MotionValidatorPtr MoValid(new ca::BVPMotionValidator(si_xyzpsi));
        si_xyzpsi->setMotionValidator(MoValid);
        si_xyzpsi->setup();

        ob::PlannerPtr bitstar(new og::BITstar(si_xyzpsi));

        ob::ProblemDefinitionPtr pdef(new ob::ProblemDefinition(si_xyzpsi));
        pdef->setStartAndGoalStates(start_ptr, goal_ptr);
//        pdef->setOptimizationObjective(ob::OptimizationObjectivePtr(new ob::PathLengthOptimizationObjective(si_xyzpsi)));
//        pdef->setOptimizationObjective(ob::OptimizationObjectivePtr(new ca::kite_bvp_solver::BVPObjective(si_xyzpsi)));
//        todo leak check
        ob::OptimizationObjectivePtr obj(new ca::kite_bvp_solver::BVPObjective(si_xyzpsi));
        obj->setCostToGoHeuristic(&ca::kite_bvp_solver::goalCostToGo);
        pdef->setOptimizationObjective(obj);
        bitstar->setProblemDefinition(pdef);
        bitstar->setup();
        pub_obstacles_marker_array.publish(obstacle_set.GetMarkerArray(1, 0, 0, 0.7));
        ob::PlannerStatus solved = bitstar->solve(100);
        if(solved == ob::PlannerStatus::EXACT_SOLUTION) {
            ROS_INFO("Solved");
            boost::shared_ptr<og::PathGeometric> path = boost::static_pointer_cast<og::PathGeometric>(bitstar->getProblemDefinition()->getSolutionPath());
//            path->interpolate(std::max(20, (int)path->getStateCount()));
            auto final_bit = std::make_shared<pc::PathWaypoint> (si_xyzpsi);
            final_bit->Clear();
            pc::PathWaypoint final(si_xyzpsi);
            final.Clear();
            for (std::size_t i = 0 ; i < path->getStateCount(); i++) {
                ob::ScopedState<ca::XYZPsiStateSpace> output(si_xyzpsi);
                const ompl::base::State* input_state = path->getState(i);
                final_bit->AppendWaypoint(input_state);
            }
            auto final_bvp = std::make_shared<pc::PathWaypoint> (si_xyzpsi);
            final_bvp->Clear();
            bvp_utils::getBVPPath(path, final_bvp,true);
            ob::PlannerData data(si_xyzpsi);
            bitstar->getPlannerData(data);
            while(1) {
                pub_obstacles_marker_array.publish(obstacle_set.GetMarkerArray(1, 0, 0, 0.7));
                pub_graph_marker.publish(pc::visualization_utils::GetGraph(data, 100, 1, 0, 0, 1, 0.3));

                pub_path_bit.publish(vu::GetMarker(*final_bit.get(), 1, 0, 1, 0, 1));

                pub_path_bvp.publish(vu::GetMarker(*final_bvp.get(), 1, 1, 0, 0, 1));
            }
        }

    }

private:



};






int main(int argc, char **argv) {
    ros::init(argc, argv, "virtual");
    ros::NodeHandle n("~");

    planner planner;
    pub_path_bit = n.advertise<visualization_msgs::Marker>("path_bit", 0);
    pub_path_bvp = n.advertise<visualization_msgs::Marker>("path_bvp", 0);

    pub_obstacles_marker_array = n.advertise<visualization_msgs::MarkerArray>("obstacles", 0);
    pub_graph_marker = n.advertise<visualization_msgs::Marker>("graph", 1);


    ob::SpaceInformationPtr si_xyzpsi = xsu::GetStandardXYZPsiSpacePtr();
    ob::ScopedState<ca::XYZPsiStateSpace> start(si_xyzpsi), goal(si_xyzpsi);
    start->SetXYZ(Eigen::Vector3d(0,3,25.0));

    start->SetPsi(M_PI/2);
    goal->SetXYZ(Eigen::Vector3d(0,150,25.0));

    goal->SetPsi(M_PI/2);
    ROS_INFO("Planning");

    while(ros::ok())
    {
        planner.plan(start.get(), goal.get());
        ros::spinOnce();
    }

    return 0;
}
//}
