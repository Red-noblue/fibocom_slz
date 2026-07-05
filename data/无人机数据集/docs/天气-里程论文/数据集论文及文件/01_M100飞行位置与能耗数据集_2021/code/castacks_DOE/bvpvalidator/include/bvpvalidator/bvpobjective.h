//
// Created by jay on 8/6/19.
//

#ifndef BVPVALIDATOR_INCLUDE_BVPOBJECTIVE_H
#define BVPVALIDATOR_INCLUDE_BVPOBJECTIVE_H


#include "ompl/base/OptimizationObjective.h"
#include "../../bvp_doe/include/kite_bvp_solver/guess.h"
#include "../../bvpvalidator/include/bvpvalidator/bvp_utils.h"
#include "ompl/base/objectives/PathLengthOptimizationObjective.h"
#include "../../bvpvalidator/include/bvpvalidator/trochoids.h"
#include "../../bvpvalidator/include/bvpvalidator/trochoid_utils.h"

#include "Wind_graph_data.h"
namespace ob = ompl::base;

namespace ca
{
    namespace kite_bvp_solver
    {

        class BVPObjective : public ob::OptimizationObjective {
        public:

            boost::shared_ptr<Wind_graph_data> wind_query;

            boost::shared_ptr<ca::kite_bvp_solver::Init> init;
            typedef boost::shared_ptr<BVPObjective> Ptr;


            BVPObjective(const ob::SpaceInformationPtr &si,boost::shared_ptr<Wind_graph_data> wind);


            virtual ob::Cost motionCost(const ob::State *s1, const ob::State *s2) const;

            virtual ob::Cost motionCostHeuristic(const ob::State *s1, const ob::State *s2) const;
            virtual ob::InformedStateSamplerPtr allocInformedStateSampler(const ob::StateSpace* space, const ob::ProblemDefinitionPtr probDefn, const ob::Cost* bestCost) const;

//            virtual ob::Cost
        };
        ob::Cost goalCostToGo(const ob::State* state, const ob::Goal* goal);
#define EPSILON (10e-10)

        typedef enum
        {
            L_SEG = 0,
            S_SEG = 1,
            R_SEG = 2
        } SegmentType;

/* The segment types for each of the Path types */
        const SegmentType DIRDATA[][3] = {
                { L_SEG, S_SEG, L_SEG },
                { L_SEG, S_SEG, R_SEG },
                { R_SEG, S_SEG, L_SEG },
                { R_SEG, S_SEG, R_SEG },
                { R_SEG, L_SEG, R_SEG },
                { L_SEG, R_SEG, L_SEG }
        };
        typedef enum
        {
            LSL = 0,
            LSR = 1,
            RSL = 2,
            RSR = 3,
            RLR = 4,
            LRL = 5
        } DubinsPathType;

        typedef struct
        {
            double alpha;
            double beta;
            double d;
            double sa;
            double sb;
            double ca;
            double cb;
            double c_ab;
            double d_sq;
        } DubinsIntermediateResults;

        typedef struct
        {
            /* the initial configuration */
            double qi[3];
            /* the lengths of the three segments */
            double param[3];
            /* model forward velocity / model angular velocity */
            double rho;
            /* the path type described */
            DubinsPathType type;
        } DubinsPath;

#define EDUBOK        (0)   /* No error */
#define EDUBCOCONFIGS (1)   /* Colocated configurations */
#define EDUBPARAM     (2)   /* Path parameterisitation error */
#define EDUBBADRHO    (3)   /* the rho value is invalid */
#define EDUBNOPATH    (4)   /* no connection between configurations with this word */


        typedef int (*DubinsPathSamplingCallback)(double q[3], double t, void* user_data);


        int dubins_shortest_path(DubinsPath* path, double q0[3], double q1[3], double rho);


        int dubins_path(DubinsPath* path, double q0[3], double q1[3], double rho, DubinsPathType pathType);

        double dubins_path_length(DubinsPath* path);

        double dubins_segment_length(DubinsPath* path, int i);


        double dubins_segment_length_normalized( DubinsPath* path, int i );

        DubinsPathType dubins_path_type( DubinsPath* path );

        int dubins_path_sample(DubinsPath* path, double t, double q[3]);

        int dubins_path_sample_many(DubinsPath* path,
                                    double stepSize,
                                    DubinsPathSamplingCallback cb,
                                    void* user_data);
        int dubins_path_endpoint(DubinsPath* path, double q[3]);


        int dubins_extract_subpath(DubinsPath* path, double t, DubinsPath* newpath);


        int dubins_word(DubinsIntermediateResults* in, DubinsPathType pathType, double out[3]);
        int dubins_intermediate_results(DubinsIntermediateResults* in, double q0[3], double q1[3], double rho);

        double fmodr( double x, double y);


        double mod2pi( double theta );

        void dubins_segment( double t, double qi[3], double qt[3], SegmentType type);

        int dubins_LSL(DubinsIntermediateResults* in, double out[3]);
        int dubins_RSR(DubinsIntermediateResults* in, double out[3]);


        int dubins_LSR(DubinsIntermediateResults* in, double out[3]);


        int dubins_RSL(DubinsIntermediateResults* in, double out[3]);

        int dubins_RLR(DubinsIntermediateResults* in, double out[3]);


        int dubins_LRL(DubinsIntermediateResults* in, double out[3]);


    }
}


#endif //BITSTAR3D_BVPOBJECTIVE_H
