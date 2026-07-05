//
// Created by jay on 8/30/19.
//

#include "../include/bvpvalidator/trochoids.h"

namespace ang = ca::math_utils::angular_math;

typedef std::vector<std::tuple<double,double,double> > Path;



Path ca::trochoids::Trochoid::getTrochoid() {
    //Establishing some variables
    std::vector<std::pair<double,double> > del;
    del.push_back(std::make_pair<double,double>(1,1));
    del.push_back(std::make_pair<double,double>(1,-1));
    del.push_back(std::make_pair<double,double>(-1,1));
    del.push_back(std::make_pair<double,double>(-1,-1));
    double best_length = std::numeric_limits<double>::infinity();
    Path final_path;
    psi_w = ang::WrapTo2Pi(atan2(problem.wind[1],problem.wind[0]));
    double x0 = problem.X0[0]*cos(psi_w) + problem.X0[1]*sin(psi_w);
    double y0 = -problem.X0[0]*sin(psi_w) + problem.X0[1]*cos(psi_w);
    double xf = problem.Xf[0]*cos(psi_w) + problem.Xf[1]*sin(psi_w);
    double yf = -problem.Xf[0]*sin(psi_w) + problem.Xf[1]*cos(psi_w);


    for (int g=0;g<4;g++) {
//    int g = 0;
//    std::cout<<g<<std::endl;

        del1 = del[g].first;
        del2 = del[g].second;
        v = problem.v;
        w = problem.max_kappa;
        vw = sqrt(pow(problem.wind[1], 2) + pow(problem.wind[0], 2));
        phi1 = ang::WrapTo2Pi(problem.X0[2] - atan2(problem.wind[1], problem.wind[0]));
        phi2 = ang::WrapTo2Pi(problem.Xf[2] - atan2(problem.wind[1], problem.wind[0]) - del2 * 2 * M_PI);
        xt10 = x0 - (v / (del1 * w)) * sin(phi1);
        yt10 = y0 + (v / (del1 * w)) * cos(phi1);
        xt20 = xf - (v / (del2 * w)) * sin(phi2 + del2 * 2 * M_PI) - vw * (2 * M_PI / w);
        yt20 = yf + (v / (del2 * w)) * cos(phi2 + del2 * 2 * M_PI);

        E = v * (((vw * (del1 - del2)) / (del1 * del2 * w)) - (yt20 - yt10));
        G = vw * (yt20 - yt10) + ((v * v * (del2 - del1)) / (del1 * del2 * w));
//        std::cout<<yt10<<" "<<yt20<<std::endl;

        for (double k = -3; k <= 3; k++) {

            double t = 0;
            std::vector<double> t1;
            while (t < (2 * 2 * M_PI / w)) {
                double t1_ = newtonRaphson(t,k);
//        std::cout<<t1_<<k<<std::endl;
                t += 1.0;
                if (t1_ > 0.0 && t1_ < 2 * 2 * M_PI / w && abs(func(t1_,k))<0.1) {
                    t1.push_back(t1_);
                }


            }

            std::sort(t1.begin(), t1.end());
            auto last = std::unique(t1.begin(), t1.end(), [](double l, double r) { return std::abs(l - r) < 1.0; });
            t1.erase(last, t1.end());
//        for(int h=0;h< t1.size();h++) {
//            std::cout << t1[h] << " " << func(t1[h], k) << " " << k << std::endl;
//        }
            for (int i = 0; i < t1.size(); i++) {


                double t2 = (del1 / del2) * t1[i] + ((ang::WrapTo2Pi(phi1 - phi2) + 2 * k * M_PI) / (del2 * w));
//            std::cout<<t2<<std::endl;
                if (t2 <= -(2 * M_PI / w) || t2 > (2 * M_PI / w))
                    continue;

                double x1t2 = (v / (del1 * w)) * sin(del1 * w * t1[i] + phi1) + vw * t1[i] + xt10;
                double y1t2 = -(v / (del1 * w)) * cos(del1 * w * t1[i] + phi1) + yt10;
                double x2t2 = (v / (del2 * w)) * sin(del2 * w * t2 + phi2) + vw * t2 + xt20;
                double y2t2 = -(v / (del2 * w)) * cos(del2 * w * t2 + phi2) + yt20;


                double alpha  =atan2(v*sin(del1*w*t1[i]+phi1),v*cos(del1*w*t1[i]+phi1) + vw );
//                std::cout<<t1[i]<<" "<<t2<<" "<< ang::WrapTo2Pi(atan2(y2t2 - y1t2, x2t2 - x1t2))-ang::WrapTo2Pi(alpha)<<std::endl;
                if (abs(ang::WrapTo2Pi(atan2(y2t2 - y1t2, x2t2 - x1t2))-ang::WrapTo2Pi(alpha))>M_PI/2.0)
                {continue;}

//            std::cout<<t1[i]<<" "<<t2<<" "<<getLength(getPath(t1[i], t2))<<" "<<k<<func(t1[i],k)<<std::endl;
                double length = getLength(getPath(t1[i], t2));
                if (length < best_length) {
                    best_length = length;
                    final_path = getPath(t1[i], t2);
//                std::cout << best_length << std::endl;
                }
            }
        }
    }

    return final_path;
}

Path ca::trochoids::Trochoid::getPath(double t1, double t2) {
    Path path;
    for (double t = 0.0; t<t1 ; t += 0.1)
    {
        double x = (v/(del1*w))*sin(del1*w*t+phi1) + vw*t + xt10;
        double y = -(v/(del1*w))*cos(del1*w*t+phi1) + yt10;
        double psi = ang::WrapTo2Pi(del1*w*t+phi1);
//        std::cout<<y<<std::endl;
        double xt = x*cos(psi_w) - y*sin(psi_w);
        double yt = x*sin(psi_w) + y*cos(psi_w);
        psi = ang::WrapTo2Pi(psi + psi_w);
        path.push_back(std::make_tuple(xt,yt,psi));

    }
    for (double t = 0; t<1 ; t += 0.01)
    {

        double x1t2 = (v / (del1 * w)) * sin(del1 * w * t1 + phi1) + vw * t1 + xt10;
        double y1t2 = -(v / (del1 * w)) * cos(del1 * w * t1 + phi1) + yt10;
        double x2t2 = (v / (del2 * w)) * sin(del2 * w * t2 + phi2) + vw * t2 + xt20;
        double y2t2 = -(v / (del2 * w)) * cos(del2 * w * t2 + phi2) + yt20;
        double x = x1t2 - t*(x1t2 - x2t2);
        double y = y1t2 - t*(y1t2 - y2t2);
        double psi = ang::WrapTo2Pi(atan2(y2t2 - y1t2, x2t2 - x1t2));
        double xt = x*cos(psi_w) - y*sin(psi_w);
        double yt = x*sin(psi_w) + y*cos(psi_w);
        psi = ang::WrapTo2Pi(psi + psi_w);

        path.push_back(std::make_tuple(xt,yt,psi));

    }

    for (double t = t2; t<(2*M_PI/w) ; t += 0.1)
    {
        double x = (v/(del2*w))*sin(del2*w*t+phi2) + vw*t + xt20;
        double y = -(v/(del2*w))*cos(del2*w*t+phi2) + yt20;
        double psi = ang::WrapTo2Pi(del2*w*t+phi2);
        double xt = x*cos(psi_w) - y*sin(psi_w);
        double yt = x*sin(psi_w) + y*cos(psi_w);
        psi = ang::WrapTo2Pi(psi + psi_w);

        path.push_back(std::make_tuple(xt,yt,psi));

    }
    return path;

}

double ca::trochoids::Trochoid::getLength(Path path) {
//    auto path = getPath(t1,t2);
    double length(0.0);
    for (int i=0; i<path.size()-1;i++)
    {

        length += sqrt(pow(std::get<0>(path[i])-std::get<0>(path[i+1]),2)+pow(std::get<1>(path[i])-std::get<1>(path[i+1]),2));
//                        std::cout<<length<<" "<<std::get<1>(path[i+1])<<std::endl;

    }
    return length;

}

double ca::trochoids::Trochoid::func(double t, double k) {

    double F = v*((xt20-xt10)+vw*(t*((del1/del2)-1)+(((ang::WrapTo2Pi(phi1-phi2)+2*k*M_PI)/(del2*w)))));

    return E*cos(del1*w*t+phi1) + F*sin(del1*w*t+phi1)-G;

}

double ca::trochoids::Trochoid::derivfunc(double t, double k) {

    double F = v*((xt20-xt10)+vw*(t*((del1/del2)-1)+(((ang::WrapTo2Pi(phi1-phi2)+2*k*M_PI)/(del2*w)))));

    return -E*del1*w*sin(del1*w*t+phi1)+F*del1*w*cos(del1*w*t + phi1)+ v*vw*((del1/del2)-1)*sin(del1*w*t+phi1);
}
double ca::trochoids::Trochoid::newtonRaphson(double x,double k)
{
    double h = func(x,k) / derivfunc(x,k);
    int iter = 0;
    while (abs(h) >= EPSILON)
    {
        h = func(x,k)/derivfunc(x,k);

        iter++;
        if (iter > 1000)
        {
            break;
        }
        x = x - h;
//        std::cout<<trial<<std::endl;
    }
    return x;

}
