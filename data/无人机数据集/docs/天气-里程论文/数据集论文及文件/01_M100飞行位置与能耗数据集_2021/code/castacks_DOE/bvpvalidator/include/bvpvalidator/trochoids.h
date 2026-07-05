//
// Created by jay on 8/30/19.
//

#ifndef TROCHOIDS_H
#define TROCHOIDS_H

#define EPSILON 0.0001
#include <math.h>
#include <vector>
#include <iostream>
#include <memory>
#include "math_utils/math_utils.h"

namespace ca{
    namespace trochoids{


        class Trochoid {


            double  del1, del2, v, w, vw, phi1, phi2, psi_w;
            double xt10, yt10, xt20, yt20, E, G;


        public:
            typedef std::vector<std::tuple<double,double,double> > Path;

            struct Problem {
                std::vector<double> X0;
                std::vector<double> Xf;
                std::vector<double> wind;
                double max_kappa;
                double v;

            };
            Problem problem;
            Trochoid(){};

            Path getTrochoid();

            double func(double t,double k);

            double derivfunc(double t, double k);

            double newtonRaphson(double x,double k);

            double getLength(Path path);

            Path getPath(double t1 ,double t2);
        };
    }

}



#endif //BITSTAR3D_TROCHOIDS_H
