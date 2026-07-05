# Combined Data used for the export of the CSV
#
Header header
anemometer/Anemometer wind
# Battery Data
float32 voltage
float32 current
# Odom position
geometry_msgs/Point odom_position
float64[36] odom_position_covariance
# Odom Orientation
geometry_msgs/Quaternion odom_orientation
# Odom Linear Velocity
geometry_msgs/Twist odom_velocity
float64[36] odom_velocity_covariance
# IMU linear accel
geometry_msgs/Vector3 imu_linear_accel
float64[9] imu_linear_accel_covariance