#include <iostream>
#include "../include/Wind_graph_data.h"
using namespace std;
// positions in the CSV
#define scale_factor 400 // scaling factor from x-y to actual meters
const double min_x = -7.55109; // extents for the data (found using min and max of column)
const double min_y = -3.25;
const double max_x = 4.00121;
const double max_y = 3.25;
const double inc_x = 0.012409;
const double inc_y = 0.0125;


int main() {
    Wind_graph_data g(min_x, min_y, max_x, max_y, inc_x, inc_y, scale_factor);
    for (int i = 20; i <= 25; i += 5) { // insert data
        cout << i << endl;
        g.cv2_layer((const string) "/home/raven/Code/Data/EMBARK/wind_data/wind_processed/f" + to_string(i) + ".csv", i);
    }
    cout << "Done reading" << endl;
//    auto x = g.query_1d_data(3.9, 2, 5.05);
    auto x = g.query_2d_data(min_x, min_y, max_x, max_y, 22);
    cout << x;
    cout << "Done querying" << endl;
    g.display_image(22.0);
    return 0;
}