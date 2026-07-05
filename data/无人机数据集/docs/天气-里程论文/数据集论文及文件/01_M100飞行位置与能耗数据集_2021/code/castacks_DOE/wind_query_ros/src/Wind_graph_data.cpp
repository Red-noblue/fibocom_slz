//
// Created by raven on 7/19/19.
//

#include "Wind_graph_data.h"

/// Constructor that defines the extents of the wind data
/// \param x_min
/// \param y_min
/// \param x_max
/// \param y_max
/// \param x_inc X axis increment (size per cell)
/// \param y_inc Y axis increment
Wind_graph_data::Wind_graph_data(double x_min, double y_min, double x_max, double y_max, double x_inc, double y_inc, double sf) {
    // Fills out this->x and this->y
    // todo check this to make sure we dont overallocate space (1 extra in y???)
    for (double i = x_min; i <= x_max; i += x_inc)
        this->x.insert(i);
    for (double i = y_min; i <= y_max; i += y_inc)
        this->y.insert(i);
    this->x.insert(x_max);
    this->y.insert(y_max);
    scale_factor = sf;
}

/// Function to read and add a layer of wind data
/// \param path full location of the CSV wind data
/// \param z Altitude assocuated with the slice
void Wind_graph_data::cv2_layer(const string path, double z) {
    int size[2] = {(int) x.size(), (int) y.size()};
    cv::Mat new_layer(2, size, CV_64FC4, cv::Scalar(0)); //Doing it as a multi channel thing
    std::ifstream file(path.c_str());
    string line = "";
    // Skip first line, which has labels
    getline(file, line);
    // Iterate through each line and split the content using delimeter
    while (file.good()) {
        vector<double> vec_double;
        vector<string> vec;
        getline(file, line);
        if (line.size() <= 1) // Make sure we didn't read a blank line
            continue;
        boost::algorithm::split(vec, line, boost::is_any_of(","));
        // convert to double
        transform(vec.begin(), vec.end(), back_inserter(vec_double), boost::lexical_cast<double, string>);
        // Find pos to store
        int *pos = find_pos(vec_double[x_pos], vec_double[y_pos]);
        //store
        if (vec_double[3])
            new_layer.at<cv::Vec4d>(pos[0], pos[1]) = {vec_double[0], vec_double[1], vec_double[2], vec_double[3]};
        else
            new_layer.at<cv::Vec4d>(pos[0], pos[1]) = {NAN, NAN, NAN, 0};
        delete pos;
    }
    // Close the File
    file.close();
    // Sort vector of vector using
    this->z.insert(z);
    mat_data.insert(pair<double, cv::Mat>(z, new_layer));
}

int *Wind_graph_data::find_pos(double x, double y) {
    int *pos = new int[2];
    pos[0] = distance(this->x.begin(), this->x.lower_bound(x));
    pos[1] = distance(this->y.begin(), this->y.lower_bound(y));
    return pos;
}

/// Returns the 2 closest matching layers (unless it is the end that matches)
/// \param z altutude
/// \return double [2] of prv z and next z that the queried z falls between
double *Wind_graph_data::find_slice(double z) {
    double *matches = new double[2];
    auto it = this->z.upper_bound(z);
    if (it == this->z.end()) {
        it = prev(this->z.end());
        matches[1] = *(it);
        matches[0] = *(it);
    } else {
        matches[1] = *(it);
        it = prev(it);
        matches[0] = *(it); // one before the one greater than z
    }
    return matches;
}

cv::Vec<double, 4> Wind_graph_data::query_1d_data(double x, double y, double z) {
    x /= scale_factor;
    y /= scale_factor;
    int *pos = find_pos(x, y);
    // todo handle the case where set doesn't find the match we need
    // todo make this equal_range and then allow the code to round off to the closest match (impossible to match exactly otherwise)
    double *closest_matches = find_slice(z);
    cv::Vec4d value_1 = mat_data[closest_matches[0]].at<cv::Vec4d>(pos[0], pos[1]);
    cv::Vec4d value_2 = mat_data[closest_matches[1]].at<cv::Vec4d>(pos[0], pos[1]);
    delete pos;
    if (closest_matches[1] != closest_matches[0] && value_1[3] != 0 && value_2[3] != 0) {
        double factor = (z - closest_matches[0]) / (closest_matches[1] - closest_matches[0]);
        delete closest_matches;
        return (value_1 * (1 - factor) + factor * value_2);
    } else if (value_2[3] == invalid)
        return value_1;
    else
        return value_2;
}

cv::Vec4d Wind_graph_data::query_2d_data(double x1, double y1, double x2, double y2, double z) {
    // todo handle the case where set doesn't find the match we need
    // todo make this equal_range and then allow the code to round off to the closest match (impossible to match exactly otherwise)
    // todo make all pointers auto pointers so we dont forget to cleaner them
    // fix scale
    x1 /= scale_factor;
    y1 /= scale_factor;
    x2 /= scale_factor;
    y2 /= scale_factor;
    int *pos1 = find_pos(x1, y1);
    int *pos2 = find_pos(x2, y2);
    double *closest_matches = find_slice(z);
    int roi_x = min(pos1[0], pos2[0]);
    int roi_y = min(pos1[1], pos2[1]);
    int roi_x2 = max(pos1[0], pos2[0]);
    int roi_y2 = max(pos1[1], pos2[1]);
    if (roi_x == roi_x2)
        roi_x2++;
    if (roi_y == roi_y2)
        roi_y2++;
    cv::Range ranges[3];
    ranges[0] = cv::Range(roi_x, roi_x2);
    ranges[1] = cv::Range(roi_y, roi_y2);
    ranges[2] = cv::Range(0, 4);
    auto roi_1 = mat_data[closest_matches[0]](ranges);
    auto roi_2 = mat_data[closest_matches[1]](ranges);
    cv::Vec4d mean_1 = mean(roi_1);
    cv::Vec4d mean_2 = mean(roi_2);
    delete pos1;
    delete pos2;
    if (closest_matches[1] != closest_matches[0]) {
        double factor = (z - closest_matches[0]) / (closest_matches[1] - closest_matches[0]);
        delete closest_matches;
        return (mean_1 * (1 - factor) + factor * mean_2);
    } else
        return mean_1;
}


Wind_graph_data::~Wind_graph_data() {
    for (auto i:mat_data)
        i.second.release();
}

void Wind_graph_data::display_image(double z) {
    double *closest_matches = find_slice(z);
    cv::imshow("Prv layer", mat_data[closest_matches[0]]);
    cv::waitKey(0);
}

cv::Vec4d Wind_graph_data::mean(cv::Mat &I) {
    // Function to calculate the mean while not including invalid cells
    int count = 0;
    cv::Vec4d mean = {0, 0, 0, 0};
    cv::MatIterator_<cv::Vec4d> it, end;
    for (it = I.begin<cv::Vec4d>(), end = I.end<cv::Vec4d>(); it != end; ++it) {
        if ((*it)[3] == invalid)
            continue;
        mean[0] += (double) (*it)[0];
        mean[1] += (double) (*it)[1];
        mean[2] += (double) (*it)[2];
        mean[3] += (double) (*it)[3]; // The mean should be 1, more for debugging
        count++;
    }
    return mean / count;
}


