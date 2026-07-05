//
// Created by jay on 7/28/19.
//
#include <utility>
#include <map>
#include <fstream>
#include "kite_bvp_defs.h"
#include "ros/ros.h"
#include "ros/package.h"
#include <fstream>
#ifndef KITE_BVP_SOLVER_INCLUDE_GUESS_H
#define KITE_BVP_SOLVER_INCLUDE_GUESS_H

namespace ca {
    namespace kite_bvp_solver {
        class Init {
        private:
            struct pos{
                int x, y, psi;
            };
            int x_inc, y_inc, wind_trial;

            std::vector<std::pair<pos, double>> wind_LUT;
        public:
            std::vector<double> init_guess;
            double x_seed,y_seed;
            std::map<int, std::map<int, std::map<int, std::vector<double>>>> LUT;

            Init(std::string filename) {
                srand(time(NULL));
                std::string s = ros::package::getPath("kite_bvp_solver");
                std::cout << "Loading database from " << filename << std::endl;
                std::string value;
                filename = s + "/include/kite_bvp_solver/" + filename;
                std::ifstream f(filename);
                std::vector<double> q(14); //todo make this a variable (read it from the first row)
                while (f.good()) {
                    getline(f, value);
                    std::istringstream iss(value);
                    double i;
                    int j = 0;
                    while (iss >> i) {
                        q[j] = i;
                        j++;
                        if (iss.peek() == ',')
                            iss.ignore();
                    }
                    // fill out LUT
                    std::vector<double> guess(q.end() - 11, q.end());
                    LUT[int(q[0])][int(q[1])][int(q[2])] = guess;
                    //fill out wind_LUT
                    wind_LUT.push_back(std::make_pair(pos({(int)q[0], (int)q[1], (int)q[2]}), guess[8] + guess[9] + guess[10]));
                }
                std::cout<<"done"<<std::endl;
                reset();
            }
            void reset()
            { // MUST BE CALLED MANUALLY ONCE A SOLUTION HAS BEEN FOUND OR NOT
                x_inc = 0;
                y_inc = 0;
                wind_trial = 0;
            }
            bool getInit(BVProblem &problem_)
            {
                auto og_x = problem_.Xf[0], og_y = problem_.Xf[1];
                bool  valid = false;
                for (int trial = 0; trial<35; trial++) {
                    getNextInit(problem_);
                    problem_.Xf[0] = og_x + x_inc;
                    problem_.Xf[1] = og_y + y_inc;
                    valid = getCloseInit(problem_);
                    if (valid)
                        return valid;
                }
                return false;


            }

            void getInitScaled(BVProblem problem_, double wind[2], double v=5){

                double scale = fmax(abs(problem_.Xf[0]),abs(problem_.Xf[1]))/80.0;
                std::cout<<scale<<std::endl;
                int x = roundUp(problem_.Xf[0]/scale,5);
                int y = roundUp(problem_.Xf[1]/scale,5);
                int psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);
                if (psi == 360){
                    psi = 0;
                }
                std::cout<<x<<" "<<y<<" "<<psi<<std::endl;
                auto q = LUT[x][y][psi];

                for (int i=0;i<4;i++){
                    q[i] = q[i]/pow(scale,i+2);
                    q[i+4] = q[i+4]/pow(scale,i+2);
                }
                q[8] = q[8]*scale;
                q[9] = q[9]*scale;
                q[10] = q[10]*scale;
                init_guess =q;

            }

            void getInitWindScaled(BVProblem problem_, double wind[2], double v=5){

                double scale = fmax(abs(problem_.Xf[0]),abs(problem_.Xf[1]))/30.0;
                std::cout<<scale<<std::endl;
                int x = roundUp(problem_.Xf[0]/scale,5);
                int y = roundUp(problem_.Xf[1]/scale,5);
                int psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);

                if (psi == 360){
                    psi = 0;
                }
                std::cout<<x<<" "<<y<<" "<<psi<<std::endl;
                auto q = LUT[x][y][psi];

                double s = (q[8]+q[9]+q[10])*scale;
                double xs = problem_.Xf[0]-(s*wind[0]/v);
                double ys = problem_.Xf[1]-(s*wind[1]/v);
                scale = fmax(fabs(xs),fabs(ys))/30.0;
                std::cout<<xs<<" "<<ys<<" "<<psi<<std::endl;

                x = roundUp(xs/scale,5);
                y = roundUp(ys/scale,5);
                q = LUT[x][y][psi];
                std::cout<<x<<" "<<y<<" "<<psi<<std::endl;
                std::cout<<scale<<std::endl;

                for (int i=0;i<4;i++){
                    q[i] = q[i]/pow(scale,i+2);
                    q[i+4] = q[i+4]/pow(scale,i+2);
                }
                q[8] = q[8]*scale;
                q[9] = q[9]*scale;
                q[10] = q[10]*scale;
                init_guess =q;


            }

            void getInitBucket(BVProblem problem_, double wind[2], double v=5) {
                int size = 50;
                int step= 5 ;
                int x = roundUp(problem_.Xf[0], 5);
                int y = roundUp(problem_.Xf[1], 5);
                int psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);
                double s = 0;
                if (psi == 360) {
                    psi = 0;
                }
                if (LUT.count(x) && LUT[x].count(y) && LUT[x][y].count(psi)) {
                    auto q = LUT[x][y][psi];
                    s = (q[8] + q[9] + q[10]);
                } else {
                    for (int i; i < 10; i++) {
//                        std::cout<<i<<std::endl;
                        x = roundUp(problem_.Xf[0] + (2.0 * (rand() / (double) RAND_MAX) - 1.0) * 10.0, 5);
                        y = roundUp(problem_.Xf[1] + (2.0 * (rand() / (double) RAND_MAX) - 1.0) * 10.0, 5);
                        psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);
                        if (LUT.count(x) && LUT[x].count(y) && LUT[x][y].count(psi)) {
                            auto q = LUT[x][y][psi];
                            s = (q[8] + q[9] + q[10]);

                            break;
                        }
                        assert(i!=9);
                    }


                }

                double xs = roundUp(problem_.Xf[0] - (s * wind[0] / v), step);
                double ys = roundUp(problem_.Xf[1] - (s * wind[1] / v), step);
//                std::cout<<xs<<" "<<ys<<std::endl;

                int x_min = fmax(-600, xs - size);
                int x_max = fmin(600, xs + size);
                int y_min = fmax(-600, ys - size);
                int y_max = fmin(600, ys + size);
                x = x_min;
                double cost = std::numeric_limits<double>::infinity();
                while (x < x_max) {
                    y = y_min;
                    while (y < y_max) {
//                        std::cout<<x<<" "<<y<<" "<<std::endl;
                        if (LUT.count(x) && LUT[x].count(y) && LUT[x][y].count(psi)) {
                            auto q = LUT[x][y][psi];
                            s = (q[8] + q[9] + q[10]);
                            double offset_a = sqrt(pow(-(x - problem_.Xf[0]) - s / v * wind[0], 2) +
                                                   pow(-(y - problem_.Xf[1]) - s / v * wind[1], 2));
//                            std::cout<<x<<" "<<y<<" "<<offset_a<<std::endl;

                            if (offset_a < cost) {
                                cost = offset_a;
                                init_guess = LUT[x][y][psi];

                            }
                        }

                        y += step;
                    }
                    x += step;
                }
            }

            void getInitWindNoSort(BVProblem problem_, double wind[2], double v=5) {
                int iter = 0;
                double cost = std::numeric_limits<double>::infinity();
                for (int i = 0; i < wind_LUT.size(); i++) {
                    auto a = wind_LUT[i];
                    double diff_a1 = a.first.psi - problem_.Xf[2] * 180 / M_PI;
                    double diff_a2 = 360 - (a.first.psi - problem_.Xf[2] * 180 / M_PI);
                    double angle_a1 = fmod(diff_a1, 360) < 0 ? fmod(diff_a1, 360) + 360 : fmod(diff_a1, 360);
                    double angle_a2 = fmod(diff_a2, 360) < 0 ? fmod(diff_a2, 360) + 360 : fmod(diff_a2, 360);
                    double offset_a = sqrt(pow(-(a.first.x - problem_.Xf[0]) - a.second / v * wind[0], 2) +
                                           pow(-(a.first.y - problem_.Xf[1]) - a.second / v * wind[1], 2)) +
                                      std::min(angle_a1, angle_a2);
                    if (offset_a<cost){
                        cost = offset_a;
                        iter = i;
//                            std::cout<<iter<<std::endl;
                    }

                }
//                std::cout<<cost<<std::endl;
                init_guess = LUT[wind_LUT[iter].first.x][wind_LUT[iter].first.y][wind_LUT[iter].first.psi];
//                    std::cout<<"seednosort"<<" "<<wind_LUT[iter].first.x<<" "<<wind_LUT[iter].first.y<<" "<<wind_LUT[iter].first.psi<<std::endl;
                x_seed = wind_LUT[iter].first.x;
                y_seed = wind_LUT[iter].first.y;

            }

            void getInitWind(BVProblem problem_, double wind[2], double v=5){
//                std::cout<<wind[0]<<" "<<wind[1]<<std::endl;
                if (wind_trial == 0){
                    getInitBucket(problem_,wind);
                    wind_trial++;
                    return;

                }
                if (wind_trial == 1){
                    // New query, we need to resort using problem_.Xf
                    sort(wind_LUT.begin(), wind_LUT.end(),
                         [problem_, wind, v](const std::pair<pos, double> &a, const std::pair<pos, double> & b) -> bool
                         {
                             double diff_a1 = a.first.psi - problem_.Xf[2]*180/M_PI;
                             double diff_a2 =  360 - (a.first.psi - problem_.Xf[2]*180/M_PI);
                             double angle_a1 = fmod(diff_a1,360) < 0? fmod(diff_a1,360)+360:fmod(diff_a1,360);
                             double angle_a2 = fmod(diff_a2,360) < 0? fmod(diff_a2,360)+360:fmod(diff_a2,360);
                             double offset_a = sqrt(pow(-(a.first.x - problem_.Xf[0]) - a.second/v*wind[0], 2) + pow(-(a.first.y - problem_.Xf[1]) - a.second/v*wind[1], 2)) + std::min(angle_a1, angle_a2);
                             double diff_b1 = b.first.psi - problem_.Xf[2]*180/M_PI;
                             double diff_b2 =  360 -(b.first.psi - problem_.Xf[2]*180/M_PI);
                             double angle_b1 = fmod(diff_b1,360) < 0? fmod(diff_b1,360)+360:fmod(diff_b1,360);
                             double angle_b2 = fmod(diff_b2,360) < 0? fmod(diff_b2,360)+360:fmod(diff_b2,360);

                             double offset_b = sqrt(pow(-(b.first.x - problem_.Xf[0]) - b.second/v*wind[0], 2) + pow(-(b.first.y - problem_.Xf[1]) - b.second/v*wind[1], 2)) + std::min(angle_b1, angle_b2);
                             return offset_a < offset_b;
                         });
                }
                // optional code for profiling
                problem_.Xf[0] =wind_LUT[wind_trial].first.x;
                problem_.Xf[1] =wind_LUT[wind_trial].first.y;
                problem_.Xf[2] =wind_LUT[wind_trial].first.psi*M_PI/180;
                //

                init_guess = LUT[wind_LUT[wind_trial-1].first.x][wind_LUT[wind_trial-1].first.y][wind_LUT[wind_trial-1].first.psi];
//                    std::cout<<"seed"<<" "<<wind_LUT[wind_trial].first.x<<" "<<wind_LUT[wind_trial].first.y<<" "<<wind_LUT[wind_trial].first.psi<<std::endl;
                wind_trial++;
            }
            void getNextInit(BVProblem problem_){
                if (-x_inc > y_inc && x_inc < y_inc) // downwards in y
                    y_inc+=5;
                else if(y_inc > x_inc) // right in x
                    x_inc+=5;
                else if(x_inc > -y_inc) // up in y
                    y_inc -= 5;
                else if (x_inc >= y_inc) // left in x and move out
                    x_inc -= 5;
                else
                    y_inc -= 5;
            }

            bool getCloseInit(BVProblem &problem_) {
                bool valid = false;
                int x = roundUp(problem_.Xf[0], 5);
                int y = roundUp(problem_.Xf[1], 5);
                int psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);
                if (psi == 360){
                    psi = 0;
                }
                if (LUT.count(x) && LUT[x].count(y) && LUT[x][y].count(psi)) {

                    init_guess = LUT[x][y][psi];
                    valid = true;
                }
                return valid;

            }

            void update(int x, int y, int p, std::vector<double> q){
                LUT[x][y][p] = q;
            }
            void write_data(std::string path){
                std::ofstream file(path.c_str());
                for (auto m1 : LUT)
                    for(auto m2 : m1.second)
                        for(auto m3 : m2.second){
                            file << m1.first << ","<<m2.first <<"," << m3.first <<",";
                            for(double x:m3.second)
                                file<<x<<",";
                            file<<std::endl;
                        }
                file.close();
            }

            bool getRandInit(BVProblem &problem_) {
                //                std::vector<double> init_guess(11);

                bool valid = false;
                while (!valid) {
                    int x = roundUp(problem_.Xf[0] + (2.0 * (rand() / (double) RAND_MAX) - 1.0) * 10.0, 5);
                    int y = roundUp(problem_.Xf[1] + (2.0 * (rand() / (double) RAND_MAX) - 1.0) * 10.0, 5);
                    int psi = roundUp(problem_.Xf[2] * 180 / M_PI, 30);
                    //                    std::cout <<(2.0*(rand()/(double)RAND_MAX)-1.0)*10.0<<std::endl;
                    //                    std::cout << "Finding seed for " << x << y << psi << std::endl;
                    if (LUT.count(x) && LUT[x].count(y) && LUT[x][y].count(psi)) {
                        //                        std::cout << "Found seed for " << x << y << psi << std::endl;
                        init_guess = LUT[x][y][psi];
                        valid = true;

                    }
                }
                return valid;

            }

            int roundUp(float num, int m) {
                assert(m);
                int x = (int) num;
                //                return ((numToRound + multiple - 1) / multiple) * multiple;
                return x + ((m - (x % m)) % m);
            }

            ~Init() {
                std::cout << "Deleting database" << std::endl;
            }


        };
    }
}

#endif //BITSTAR3D_INIT_H
