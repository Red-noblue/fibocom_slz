//
// Created by jay on 8/6/19.
//

#include "../include/bvpvalidator/bvpobjective.h"
#include "ompl/base/GoalTypes.h"
#include "ompl/base/goals/GoalState.h"
#include <ctime>

extern "C" {
//#include "../../bvpvalidator/include/bvpvalidator/dubins.h"
}

namespace ob =  ompl::base;

ca::kite_bvp_solver::BVPObjective::BVPObjective(const ob::SpaceInformationPtr &si,boost::shared_ptr<Wind_graph_data> wind) :
        ob::OptimizationObjective(si)

{
    wind_query = wind;
    std::string filename = "large_data5.csv";
    description_ = "Energy";


    init = boost::shared_ptr<ca::kite_bvp_solver::Init>(new ca::kite_bvp_solver::Init(filename));

}

ompl::base::Cost ca::kite_bvp_solver::BVPObjective::motionCost(const ob::State *s1, const ob::State *s2) const {
    ca::kite_bvp_solver::BVProblem problem = bvp_utils::TfToOrigin(s1, s2);

//    init->reset();
    std::vector<double> q;
    double s;
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

    // todo read this from the wind class
    init->reset();
    init->getInitBucket(problem, wind);
    q = init->init_guess;
    init->reset();
    double v = 5.0;

    double n = q.size();
//    double sf = (q[n - 1] + q[n - 2] + q[n - 3]);
    double z1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
    double z2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
//    double z = abs(z1-z2);

    s = bvp_utils::getPathLengthfromcoeff(q,v,z2-z1,wind,100);


    return   ompl::base::Cost(s);//ob::Cost(si_->trueDistance(s1, s2));
}
ompl::base::Cost
ca::kite_bvp_solver::BVPObjective::motionCostHeuristic(const ob::State *s1,
                                                       const ob::State *s2) const
{
//    Eigen::Vector3d vec1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//    Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
//    double psi1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
//    double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
//    double q0[] = { vec1[0],vec1[1],psi1 };
//    double q1[] = { vec2[0],vec2[1],psi2 };
//    double turning_radius = 20.0;
//    DubinsPath path;
//    dubins_shortest_path( &path, q0, q1, turning_radius);
//    double s = ca::kite_bvp_solver::dubins_path_length(&path);
//    double z1 = s1->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
//    double z2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetZ();
//    double z = abs(z1-z2);

////
//    auto *s1_pt = s1->as<ca::XYZPsiStateSpace::StateType>();
//    auto *s2_pt = s2->as<ca::XYZPsiStateSpace::StateType>();
//    double mean_z = (s1_pt->GetZ() + s2_pt->GetZ())/2.0;
//    auto wind_cv = wind_query->query_2d_data(s1_pt->GetX(), s1_pt->GetY(), s2_pt->GetX(), s2_pt->GetY(), mean_z);
//    double wind[3] = {0,0,0};
//    if (!(wind_cv[3] == 0 || isnan(wind_cv[0])))
//    {
//        wind[0] = wind_cv[0];
//        wind[1] = wind_cv[1];
//    }
//    auto time = clock();
//    double s_t = ca::trochoids::getLength(s1,s2,wind);
//    double s_t = si_->heuristicDistance(s1, s2);

//    std::cout<< (double)(clock()-time)/CLOCKS_PER_SEC<<std::endl;
//    std::cout<<s1_pt->GetX()<<" "<< s1_pt->GetY()<< " "<<s1_pt->GetPsi()<<" "<< s2_pt->GetX()<< "  " << s2_pt->GetY()<<" "<<s2_pt->GetPsi()<<" "<<wind[0]<<" "<<wind[1]<<std::endl;

//    std::cout<<s_t<<std::endl;

//    return ompl::base::Cost(s_t);
//    return  ompl::base::Cost(sqrt(pow(s,2)+ pow(z,2))) ;
    return ob::Cost(si_->heuristicDistance(s1, s2));

}

ompl::base::InformedStateSamplerPtr ca::kite_bvp_solver::BVPObjective::allocInformedStateSampler(const ob::StateSpace* space, const ob::ProblemDefinitionPtr probDefn, const ob::Cost* bestCost) const
{
    return ob::InformedStateSamplerPtr(new ob::PathLengthInformedSampler(space, probDefn, bestCost));
}



ompl::base::Cost ca::kite_bvp_solver::goalCostToGo(const ob::State *state, const ob::Goal *goal) {
    const ob::GoalState* state2 = goal->as<ob::GoalState>();
//    goalRegion->
    auto s2 = state2->getState();
    Eigen::Vector3d vec1 = state->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
    Eigen::Vector3d vec2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetXYZ();
    double psi1 = state->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    double psi2 = s2->as<ca::XYZPsiStateSpace::StateType>()->GetPsi();
    double q0[] = { vec1[0],vec1[1],psi1 };
    double q1[] = { vec2[0],vec2[1],psi2 };
    double turning_radius = 20.0;
    DubinsPath path;
    dubins_shortest_path( &path, q0, q1, turning_radius);
    double s = ca::kite_bvp_solver::dubins_path_length(&path);
    std::cout<<s<<std::endl;
    return ompl::base::Cost(s);

}



int ca::kite_bvp_solver::dubins_shortest_path(DubinsPath* path, double q0[3], double q1[3], double rho)
{
    int i, errcode;
    DubinsIntermediateResults in;
    double params[3];
    double cost;
    double best_cost = INFINITY;
    int best_word = -1;
    errcode = dubins_intermediate_results(&in, q0, q1, rho);
    if(errcode != EDUBOK) {
        return errcode;
    }


    path->qi[0] = q0[0];
    path->qi[1] = q0[1];
    path->qi[2] = q0[2];
    path->rho = rho;

    for( i = 0; i < 6; i++ ) {
        DubinsPathType pathType = (DubinsPathType)i;
        errcode = dubins_word(&in, pathType, params);
        if(errcode == EDUBOK) {
            cost = params[0] + params[1] + params[2];
            if(cost < best_cost) {
                best_word = i;
                best_cost = cost;
                path->param[0] = params[0];
                path->param[1] = params[1];
                path->param[2] = params[2];
                path->type = pathType;
            }
        }
    }
    if(best_word == -1) {
        return EDUBNOPATH;
    }
    return EDUBOK;
}

int ca::kite_bvp_solver::dubins_path(DubinsPath* path, double q0[3], double q1[3], double rho, DubinsPathType pathType)
{
    int errcode;
    DubinsIntermediateResults in;
    errcode = dubins_intermediate_results(&in, q0, q1, rho);
    if(errcode == EDUBOK) {
        double params[3];
        errcode = dubins_word(&in, pathType, params);
        if(errcode == EDUBOK) {
            path->param[0] = params[0];
            path->param[1] = params[1];
            path->param[2] = params[2];
            path->qi[0] = q0[0];
            path->qi[1] = q0[1];
            path->qi[2] = q0[2];
            path->rho = rho;
            path->type = pathType;
        }
    }
    return errcode;
}

double ca::kite_bvp_solver::dubins_path_length( DubinsPath* path )
{
    double length = 0.;
    length += path->param[0];
    length += path->param[1];
    length += path->param[2];
    length = length * path->rho;
    return length;
}

double ca::kite_bvp_solver::dubins_segment_length( DubinsPath* path, int i )
{
    if( (i < 0) || (i > 2) )
    {
        return INFINITY;
    }
    return path->param[i] * path->rho;
}

double ca::kite_bvp_solver::dubins_segment_length_normalized( DubinsPath* path, int i )
{
    if( (i < 0) || (i > 2) )
    {
        return INFINITY;
    }
    return path->param[i];
}





int ca::kite_bvp_solver::dubins_path_sample( DubinsPath* path, double t, double q[3] )
{
    /* tprime is the normalised variant of the parameter t */
    double tprime = t / path->rho;
    double qi[3]; /* The translated initial configuration */
    double q1[3]; /* end-of segment 1 */
    double q2[3]; /* end-of segment 2 */
    const SegmentType* types = DIRDATA[path->type];
    double p1, p2;

    if( t < 0 || t > dubins_path_length(path) ) {
        return EDUBPARAM;
    }

    /* initial configuration */
    qi[0] = 0.0;
    qi[1] = 0.0;
    qi[2] = path->qi[2];

    /* generate the target configuration */
    p1 = path->param[0];
    p2 = path->param[1];
    dubins_segment( p1,      qi,    q1, types[0] );
    dubins_segment( p2,      q1,    q2, types[1] );
    if( tprime < p1 ) {
        dubins_segment( tprime, qi, q, types[0] );
    }
    else if( tprime < (p1+p2) ) {
        dubins_segment( tprime-p1, q1, q,  types[1] );
    }
    else {
        dubins_segment( tprime-p1-p2, q2, q,  types[2] );
    }

    /* scale the target configuration, translate back to the original starting point */
    q[0] = q[0] * path->rho + path->qi[0];
    q[1] = q[1] * path->rho + path->qi[1];
    q[2] = mod2pi(q[2]);

    return EDUBOK;
}

int ca::kite_bvp_solver::dubins_path_sample_many(DubinsPath* path, double stepSize,
                                                 DubinsPathSamplingCallback cb, void* user_data)
{
    int retcode;
    double q[3];
    double x = 0.0;
    double length = dubins_path_length(path);
    while( x <  length ) {
        dubins_path_sample( path, x, q );
        retcode = cb(q, x, user_data);
        if( retcode != 0 ) {
            return retcode;
        }
        x += stepSize;
    }
    return 0;
}

int ca::kite_bvp_solver::dubins_path_endpoint( DubinsPath* path, double q[3] )
{
    return dubins_path_sample( path, dubins_path_length(path) - EPSILON, q );
}

int ca::kite_bvp_solver::dubins_extract_subpath( DubinsPath* path, double t, DubinsPath* newpath )
{
    /* calculate the true parameter */
    double tprime = t / path->rho;

    if((t < 0) || (t > dubins_path_length(path)))
    {
        return EDUBPARAM;
    }

    /* copy most of the data */
    newpath->qi[0] = path->qi[0];
    newpath->qi[1] = path->qi[1];
    newpath->qi[2] = path->qi[2];
    newpath->rho   = path->rho;
    newpath->type  = path->type;

    /* fix the parameters */
    newpath->param[0] = fmin( path->param[0], tprime );
    newpath->param[1] = fmin( path->param[1], tprime - newpath->param[0]);
    newpath->param[2] = fmin( path->param[2], tprime - newpath->param[0] - newpath->param[1]);
    return 0;
}

int ca::kite_bvp_solver::dubins_intermediate_results(DubinsIntermediateResults* in, double q0[3], double q1[3], double rho)
{
    double dx, dy, D, d, theta, alpha, beta;
    if( rho <= 0.0 ) {
        return EDUBBADRHO;
    }

    dx = q1[0] - q0[0];
    dy = q1[1] - q0[1];
    D = sqrt( dx * dx + dy * dy );
    d = D / rho;
    theta = 0;

    /* test required to prevent domain errors if dx=0 and dy=0 */
    if(d > 0) {
        theta = mod2pi(atan2( dy, dx ));
    }
    alpha = mod2pi(q0[2] - theta);
    beta  = mod2pi(q1[2] - theta);

    in->alpha = alpha;
    in->beta  = beta;
    in->d     = d;
    in->sa    = sin(alpha);
    in->sb    = sin(beta);
    in->ca    = cos(alpha);
    in->cb    = cos(beta);
    in->c_ab  = cos(alpha - beta);
    in->d_sq  = d * d;

    return EDUBOK;
}





int ca::kite_bvp_solver::dubins_word(DubinsIntermediateResults* in, DubinsPathType pathType, double out[3])
{
    int result;
    switch(pathType)
    {
        case LSL:
            result = dubins_LSL(in, out);
            break;
        case RSL:
            result = dubins_RSL(in, out);
            break;
        case LSR:
            result = dubins_LSR(in, out);
            break;
        case RSR:
            result = dubins_RSR(in, out);
            break;
        case LRL:
            result = dubins_LRL(in, out);
            break;
        case RLR:
            result = dubins_RLR(in, out);
            break;
        default:
            result = EDUBNOPATH;
    }
    return result;
}

int ca::kite_bvp_solver::dubins_LSL(DubinsIntermediateResults* in, double out[3])
{
    double tmp0, tmp1, p_sq;

    tmp0 = in->d + in->sa - in->sb;
    p_sq = 2 + in->d_sq - (2*in->c_ab) + (2 * in->d * (in->sa - in->sb));

    if(p_sq >= 0) {
        tmp1 = atan2( (in->cb - in->ca), tmp0 );
        out[0] = mod2pi(tmp1 - in->alpha);
        out[1] = sqrt(p_sq);
        out[2] = mod2pi(in->beta - tmp1);
        return EDUBOK;
    }
    return EDUBNOPATH;
}
int ca::kite_bvp_solver::dubins_RSR(DubinsIntermediateResults* in, double out[3])
{
    double tmp0 = in->d - in->sa + in->sb;
    double p_sq = 2 + in->d_sq - (2 * in->c_ab) + (2 * in->d * (in->sb - in->sa));
    if( p_sq >= 0 ) {
        double tmp1 = atan2( (in->ca - in->cb), tmp0 );
        out[0] = mod2pi(in->alpha - tmp1);
        out[1] = sqrt(p_sq);
        out[2] = mod2pi(tmp1 -in->beta);
        return EDUBOK;
    }
    return EDUBNOPATH;
}

int ca::kite_bvp_solver::dubins_LSR(DubinsIntermediateResults* in, double out[3])
{
    double p_sq = -2 + (in->d_sq) + (2 * in->c_ab) + (2 * in->d * (in->sa + in->sb));
    if( p_sq >= 0 ) {
        double p    = sqrt(p_sq);
        double tmp0 = atan2( (-in->ca - in->cb), (in->d + in->sa + in->sb) ) - atan2(-2.0, p);
        out[0] = mod2pi(tmp0 - in->alpha);
        out[1] = p;
        out[2] = mod2pi(tmp0 - mod2pi(in->beta));
        return EDUBOK;
    }
    return EDUBNOPATH;
}

int ca::kite_bvp_solver::dubins_RSL(DubinsIntermediateResults* in, double out[3])
{
    double p_sq = -2 + in->d_sq + (2 * in->c_ab) - (2 * in->d * (in->sa + in->sb));
    if( p_sq >= 0 ) {
        double p    = sqrt(p_sq);
        double tmp0 = atan2( (in->ca + in->cb), (in->d - in->sa - in->sb) ) - atan2(2.0, p);
        out[0] = mod2pi(in->alpha - tmp0);
        out[1] = p;
        out[2] = mod2pi(in->beta - tmp0);
        return EDUBOK;
    }
    return EDUBNOPATH;
}

int ca::kite_bvp_solver::dubins_RLR(DubinsIntermediateResults* in, double out[3])
{
    double tmp0 = (6. - in->d_sq + 2*in->c_ab + 2*in->d*(in->sa - in->sb)) / 8.;
    double phi  = atan2( in->ca - in->cb, in->d - in->sa + in->sb );
    if( fabs(tmp0) <= 1) {
        double p = mod2pi((2*M_PI) - acos(tmp0) );
        double t = mod2pi(in->alpha - phi + mod2pi(p/2.));
        out[0] = t;
        out[1] = p;
        out[2] = mod2pi(in->alpha - in->beta - t + mod2pi(p));
        return EDUBOK;
    }
    return EDUBNOPATH;
}

int ca::kite_bvp_solver::dubins_LRL(DubinsIntermediateResults* in, double out[3])
{
    double tmp0 = (6. - in->d_sq + 2*in->c_ab + 2*in->d*(in->sb - in->sa)) / 8.;
    double phi = atan2( in->ca - in->cb, in->d + in->sa - in->sb );
    if( fabs(tmp0) <= 1) {
        double p = mod2pi( 2*M_PI - acos( tmp0) );
        double t = mod2pi(-in->alpha - phi + p/2.);
        out[0] = t;
        out[1] = p;
        out[2] = mod2pi(mod2pi(in->beta) - in->alpha -t + mod2pi(p));
        return EDUBOK;
    }
    return EDUBNOPATH;
}
double ca::kite_bvp_solver::fmodr( double x, double y)
{
    return x - y*floor(x/y);
}

double ca::kite_bvp_solver::mod2pi( double theta )
{
    return fmodr( theta, 2 * M_PI );
}
void ca::kite_bvp_solver::dubins_segment( double t, double qi[3], double qt[3], SegmentType type)
{
    double st = sin(qi[2]);
    double ct = cos(qi[2]);
    if( type == L_SEG ) {
        qt[0] = +sin(qi[2]+t) - st;
        qt[1] = -cos(qi[2]+t) + ct;
        qt[2] = t;
    }
    else if( type == R_SEG ) {
        qt[0] = -sin(qi[2]-t) + st;
        qt[1] = +cos(qi[2]-t) - ct;
        qt[2] = -t;
    }
    else if( type == S_SEG ) {
        qt[0] = ct * t;
        qt[1] = st * t;
        qt[2] = 0.0;
    }
    qt[0] += qi[0];
    qt[1] += qi[1];
    qt[2] += qi[2];
}
ca::kite_bvp_solver::DubinsPathType ca::kite_bvp_solver::dubins_path_type( DubinsPath* path )
{
    return path->type;
}


//ompl::base::InformedStateSamplerPtr ompl::base::PathLengthOptimizationObjective::allocInformedStateSampler(const StateSpace* space, const ProblemDefinitionPtr probDefn, const Cost* bestCost) const
//{
//    return InformedStateSamplerPtr(new PathLengthInformedSampler(space, probDefn, bestCost));
//}


