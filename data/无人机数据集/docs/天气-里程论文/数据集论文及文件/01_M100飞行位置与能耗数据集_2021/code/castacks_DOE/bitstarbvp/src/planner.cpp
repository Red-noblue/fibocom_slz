#include <iostream>
#include <ros/ros.h>
#include <tf/transform_broadcaster.h>

//#include "uav_path_planner_library/uav_path_planner_library.h"
//#include "bvpvalidator/BVPMotionValidator.h"

#include "xyzpsi_state_space/xyzpsi_state_space_utils.h"
#include "xyzpsi_state_space/xyzpsi_state_space.h"
#include "ompl/base/SpaceInformation.h"
#include "ompl/base/ScopedState.h"
#include "planning_common/utils/visualization_utils.h"
#include <ompl/geometric/planners/bitstar/BITstar.h>
#include <ompl/geometric/planners/rrt/RRT.h>
#include "planning_common/planner_data/planner_progress.h"
#include "planning_common/planner_termination/iteration_termination.h"
#include "ompl/base/PlannerTerminationCondition.h"

#include "ompl/base/objectives/PathLengthOptimizationObjective.h"
#include "ompl/base/objectives/MinimaxObjective.h"
#include <Eigen/Dense>
#include "../../bvpvalidator/include/bvpvalidator/bvpmotionvalidator.h"
#include "../../bvpvalidator/include/bvpvalidator/bvp_utils.h"
#include "../../bvpvalidator/include/bvpvalidator/bvpobjective.h"
#include "../../bvpvalidator/include/bvpvalidator/trochoid_utils.h"
#include "Wind_graph_data.h"

#include <octomap_msgs/Octomap.h>
#include <octomap_msgs/conversions.h>
#include <octomap_ros/conversions.h>
#include <octomap/octomap.h>


namespace ob = ompl::base;
namespace og = ompl::geometric;
namespace xsu = ca::xyzpsi_state_space_utils;
namespace pc = ca::planning_common;
namespace vu = pc::visualization_utils;
ros::Publisher pub_path_bit;
ros::Publisher pub_path_bvp;
boost::shared_ptr<Wind_graph_data> wind_query;
//namespace ca {
class planner {

public:

    ob::SpaceInformationPtr si_xyzpsi ;//= xsu::GetStandardXYZPsiSpacePtr();
    bool is_map ;
    std::shared_ptr<octomap::OcTree> tree;


    void updateMap(std::shared_ptr<octomap::OcTree> map)
	{
		tree = map;
		double x , y , z;
		tree ->getMetricMin(x,y,z);
		ROS_INFO(" Lower Bounds %f %f %f",x,y,z);
		Eigen::Vector3d bbmin(x,y,z);
		tree ->getMetricMax(x,y,z);
		ROS_INFO(" Upper Bounds %f %f %f",x,y,z);	
		Eigen::Vector3d bbmax(x,y,z);

		is_map = true;
		updateBounds(bbmin , bbmax);
	}
	void updateBounds(Eigen::Vector3d bbmin, Eigen::Vector3d bbmax)
    {
        ompl::base::RealVectorBounds bounds(3);
        ob::StateSpacePtr space(new ca::XYZPsiStateSpace);

        bounds.setLow(0, bbmin[0]);
        bounds.setLow(1, bbmin[1]);
        bounds.setLow(2, 20.0);

        bounds.setHigh(0, bbmax[0]);
        bounds.setHigh(1, bbmax[1]);
        bounds.setHigh(2, 100.0); //FAA limits
        space->as<ca::XYZPsiStateSpace>()->SetBounds(bounds);
        si_xyzpsi = ob::SpaceInformationPtr(new ob::SpaceInformation(space));
 //       mvp.setGlideslope(20.0);

        ob::MotionValidatorPtr MoValid(new ca::BVPMotionValidator(si_xyzpsi,wind_query));
//        si_xyzpsi->setStateValidityCheckingResolution(1/space->getMaximumExtent());

        si_xyzpsi->setMotionValidator(MoValid);
        si_xyzpsi->setStateValidityChecker(std::bind(&planner::is_valid,this,std::placeholders::_1));
        si_xyzpsi->setup();
    }
    bool is_valid(const ob::State *state)
    {
        Eigen::Vector3d pos = state->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
        octomap::point3d query(pos[0],pos[1],pos[2]);
//  		std::cout<<pos<<std::endl;
        octomap::OcTreeNode* result = tree->search(query);
        //ROS_INFO("%f",  result->getOccupancy());
        if (result->getOccupancy() >= 0.5)
        {
            return false;
        }
        else
        {
            return true;
        }

    }

	planner()
	{
		octomap::OcTree* tree = new octomap::OcTree(0.1);
        is_map = false;
		ROS_INFO("Initialized");


	}
	~planner()
	{

	}
	bool plan(const ob::State *start_ptr,const ob::State *goal_ptr,int iter)
	{
	    if (is_map)
        {
	        static bool s;
            ob::PlannerPtr bitstar(new og::BITstar(si_xyzpsi));

            ob::ProblemDefinitionPtr pdef(new ob::ProblemDefinition(si_xyzpsi));
            pdef->setStartAndGoalStates(start_ptr, goal_ptr);
//            pdef->setOptimizationObjective(ob::OptimizationObjectivePtr(new ob::PathLengthOptimizationObjective(si_xyzpsi)));
//            pdef->setOptimizationObjective(ob::OptimizationObjectivePtr(new ca::kite_bvp_solver::BVPObjective(si_xyzpsi)));
            ob::OptimizationObjectivePtr obj(new ca::kite_bvp_solver::BVPObjective(si_xyzpsi,wind_query));
            obj->setCostToGoHeuristic(&ca::kite_bvp_solver::goalCostToGo);
            pdef->setOptimizationObjective(obj);
            bitstar->setProblemDefinition(pdef);
            bitstar->setup();
            ca::PlannerProgress progress ;
            progress.set_rate(1);
            progress.StartCollectingData(bitstar);
//            ob::PlannerStatus solved = bitstar->solve(ob::PlannerTerminationCondition(pc::NumIterationsPlannerTerminationCondition(boost::bind(&og::BITstar::numIterations,bitstar->as<og::BITstar>()),15000)));
            ob::PlannerStatus solved = bitstar->solve(100);

            progress.StopCollectingData();
            if(solved == ob::PlannerStatus::EXACT_SOLUTION) {
                progress.SaveData("progress_600_2_"+ std::to_string(iter)+".csv");
                ROS_INFO("Solved");
                boost::shared_ptr<og::PathGeometric> path = boost::static_pointer_cast<og::PathGeometric>(bitstar->getProblemDefinition()->getSolutionPath());
//                path->interpolate(std::max(20, (int)path->getStateCount()));
                auto final_bit = std::make_shared<pc::PathWaypoint> (si_xyzpsi);
                final_bit->Clear();
                for (std::size_t i = 0 ; i < path->getStateCount(); i++) {
                    const ompl::base::State* input_state = path->getState(i);
                    final_bit->AppendWaypoint(input_state);
                }
                auto final_bvp = std::make_shared<pc::PathWaypoint> (si_xyzpsi);
                final_bvp->Clear();
                bool opt = true;
                s = bvp_utils::getBVPPath(si_xyzpsi,path, final_bvp,wind_query,opt);

//                std::cout<<"BVP:"<<s/(double )(iter+1)<<std::endl;
                if(final_bvp->check()&&s)
                {
                    return true;
                    std::cout<<"Passed"<<std::endl;
                }
                else{
                    return false;
                }
                bvp_utils::savePath(final_bvp,"city_bvpv2");
                final_bit->Clear();
                opt = false;
                bvp_utils::getBVPPath(si_xyzpsi,path, final_bit,wind_query,opt);
//                ca::trochoids::getTrochoidPath(path,final_bit,wind_query);
//                bvp_utils::savePath(final_bit,"trochoidsv2");
//
////
//                while(1) {
//
//
//
//                    pub_path_bit.publish(vu::GetMarker(*final_bit.get(), 2, 0, 1, 0, 1));
//                    pub_path_bvp.publish(vu::GetMarker(*final_bvp.get(), 2, 1, 0, 0, 1));
//
//                }
            }
		}
	}

private:





};


void octomapCallback(const octomap_msgs::Octomap::ConstPtr &msg, planner* planner_ptr)
{
	

	octomap::OcTree* tree = dynamic_cast<octomap::OcTree*>(octomap_msgs::msgToMap(*msg));

	// Update the octree used for collision checking
	planner_ptr->updateMap(std::shared_ptr<octomap::OcTree>(tree));
}



double get_rand(double min , double max){
    std::random_device rd;
    std::mt19937 rng(rd());
    std::uniform_real_distribution<double> uni(min,max);
    return uni(rng);
}

ob::ScopedState<ca::XYZPsiStateSpace> get_rand_state(planner planner) {
    while (1) {
        ob::SpaceInformationPtr si_xyzpsi = xsu::GetStandardXYZPsiSpacePtr();
        double x_min, y_min, z, x_max, y_max;
        planner.tree->getMetricMin(x_min, y_min, z);
        planner.tree->getMetricMax(x_max, y_max, z);
        ob::ScopedState<ca::XYZPsiStateSpace> state(si_xyzpsi);
        auto x = get_rand(x_min, x_max);
        auto y = get_rand(y_min, y_max);
        auto psi = get_rand(0, 2 * M_PI);
        state->SetXYZ(Eigen::Vector3d(x, y, 50));
        state->SetPsi(psi);
        if (planner.is_valid(state.get())) {
            return state;
        }


    }

}




int main(int argc, char **argv) {
	ros::init(argc, argv, "planner");
	ros::NodeHandle n("~");

	planner planner;

    #define scale_factor 400 // scaling factor from x-y to actual meters
    const double min_x = -7.55109; // extents for the data (found using min and max of column)
    const double min_y = -3.25;
    const double max_x = 4.00121;
    const double max_y = 3.25;
    const double inc_x = 0.012409;
    const double inc_y = 0.0125;

    wind_query = boost::shared_ptr<Wind_graph_data>(new Wind_graph_data(min_x, min_y, max_x, max_y, inc_x, inc_y, scale_factor));
        for (int i = 20; i <= 100; i += 5) { // insert data
            wind_query->cv2_layer((const std::string) "/home/jay/wind_processed/f" + std::to_string(i) + ".csv", i);
            std::cout<<"Loading wind for "<<i<<std::endl;
        }
	pub_path_bit = n.advertise<visualization_msgs::Marker>("path_bit", 0);
    pub_path_bvp = n.advertise<visualization_msgs::Marker>("path_bvp", 0);


    ros::Subscriber octamap_sub = n.subscribe<octomap_msgs::Octomap>("/octomap",1, boost::bind(&octomapCallback, _1, &planner));
	
	ob::SpaceInformationPtr si_xyzpsi = xsu::GetStandardXYZPsiSpacePtr();
	ob::ScopedState<ca::XYZPsiStateSpace> start(si_xyzpsi), goal(si_xyzpsi);
//	start->SetXYZ(Eigen::Vector3d(562,-584,50));
	start->SetXYZ(Eigen::Vector3d(-834,-437,50));
//    start->SetXYZ(Eigen::Vector3d(-1257,-119,50));


    start->SetPsi(-2.139);
//    goal->SetXYZ(Eigen::Vector3d(-2290,-206,50));
    goal->SetXYZ(Eigen::Vector3d(-1553,-390,50));
//    goal->SetXYZ(Eigen::Vector3d(-1126,-583,50));


    goal->SetPsi(-2.139);
//    ROS_INFO("Planning");


    int success = 0;
    int fail = 0;
    while(ros::ok())
    {
        if (planner.is_map) {
            for (int i = 0; i < 100; i++) {
                std::cout << "iter" << i << std::endl;


                start = get_rand_state(planner);
                goal = get_rand_state(planner);
                std::cout<<start<<std::endl;
                if(planner.plan(start.get(), goal.get(), i))
                {
                    success++;
                }
                else{
                    fail++;
                }
//                break;
                std::cout<<"S"<<success<<" "<<"F"<<fail<<std::endl;

//                break;
            }
            break;
        }
//        if(planner.is_map)
//        {
//            break;
//        }
        ros::spinOnce();



    }

	return 0;
}

  	