//
// Created by raven on 7/19/19.
//

#ifndef WIND_GRID_QUERY_WIND_GRAPH_DATA_H
#define WIND_GRID_QUERY_WIND_GRAPH_DATA_H

#include <stdio.h>
#include <vector>
#include <fstream>
#include <iterator>
#include <boost/algorithm/string.hpp>
#include <boost/lexical_cast.hpp>
#include <set>
#include <map>
#include <algorithm>
#include <opencv2/core/core.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <opencv2/highgui.hpp>

#define x_pos 4
#define y_pos 5
#define z_pos 6
#define dim_pos 3 // dimention of the position
#define invalid 0
using namespace std;

class Wind_graph_data {

private:
    map<double, cv::Mat> mat_data;// sorted cv matrices
    //   Double is z, vector is x,y (1D sorted). Final vector is for the fields inside (valid, wind_vel).
    double scale_factor;
    set<double> x;
    set<double> y;
    set<double> z;
public:
//    bool static vector_compare(const vector<double> &lhs, const vector<double> &rhs) {
//        // what do we do if lhs or rhs don't have (m_column + 1) elements?
//        return lexicographical_compare(lhs.begin() + x_pos, lhs.begin() + x_pos + dim_pos, rhs.begin() + x_pos,
//                                       rhs.begin() + x_pos + dim_pos);
//    }

    Wind_graph_data(double x_min, double y_min, double x_max, double y_max, double x_inc, double y_inc, double sf);

    void cv2_layer(string path, double z);

    int *find_pos(double x, double y);

    double *find_slice(double z);

    cv::Vec<double, 4> query_1d_data(double x, double y, double z);

    cv::Vec4d query_2d_data(double x1, double y1, double x2, double y2, double z);

    cv::Vec4d mean(cv::Mat &I);

    ~Wind_graph_data();

    void display_image(double z);
};


#endif //WIND_GRID_QUERY_WIND_GRAPH_DATA_H
