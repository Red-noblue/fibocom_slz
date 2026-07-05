#!/usr/bin/env python
'''
This script collects all data from the different sensors of a flight test and synchronizes them.
The synchronized data is saved into a new bag file and a corresponding csv file.

Written by Bastian Wagner in April 2019 at Carnegie Mellon University's Air Lab
'''

import rospy
import csv
import rosbag
import sys
from message_filters import Subscriber, ApproximateTimeSynchronizer
from sensor_msgs.msg import BatteryState, Imu
from filtering.msg import CombinedData
from anemometer.msg import Anemometer
from nav_msgs.msg import Odometry

# Get the Output file path for the data files
outpath = sys.argv[1]

# Output bagfile
bag = rosbag.Bag(outpath + "/combined.bag", "w")

# Datarows to be written to the CSV
datarows = []

# Variables needed to determine the timestamp of the first datarow
first_stamp = None
first = True


def write_files():
    """Writes the csv and bag files
    """
    bag.close()
    with open(outpath+"/combined.csv", "w") as csvfile:  # Write the CSV File
        writer = csv.writer(csvfile, delimiter=',')
        # First, write the column headers
        writer.writerow(['time', 'wind_speed', 'wind_angle', 'battery_voltage', 'battery_current', 'position', 'x', 'y', 'z', 'orientation',
                         'x', 'y', 'z', 'w', 'twist', 'linear', 'x', 'y', 'z', 'angular', 'x', 'y', 'z', 'linear_acceleration', 'x', 'y', 'z'])
        for data in datarows:
            # Gather all the data needed for a dataset
            # Calculate the time for the data
            data_time = rospy.Time(
                secs=data.header.stamp.secs, nsecs=data.header.stamp.nsecs)
            time_difference = data_time - first_stamp
            # Round the time to two decimal places
            time = round(time_difference.to_sec(), 2)
            # Read all the data
            # Wind Data
            wind_speed = data.wind.speed
            wind_angle = data.wind.angle

            # Battery Data
            battery_voltage = data.voltage
            battery_current = data.current

            # Position Data
            pos_x = data.odom_position.x
            pos_y = data.odom_position.y
            pos_z = data.odom_position.z

            # Orientation Data
            orent_x = data.odom_orientation.x
            orent_y = data.odom_orientation.y
            orent_z = data.odom_orientation.z
            orent_w = data.odom_orientation.w

            # Velocity (Twist) data
            linear_twist_x = data.odom_velocity.linear.x
            linear_twist_y = data.odom_velocity.linear.y
            linear_twist_z = data.odom_velocity.linear.z
            angular_twist_x = data.odom_velocity.angular.x
            angular_twist_y = data.odom_velocity.angular.y
            angular_twist_z = data.odom_velocity.angular.z

            # Acceleration data
            linear_accel_x = data.imu_linear_accel.x
            linear_accel_y = data.imu_linear_accel.y
            linear_accel_z = data.imu_linear_accel.z

            # Covariance Data
            pos_covariance = data.odom_position_covariance
            vel_covariance = data.odom_velocity_covariance
            acc_covariance = data.imu_linear_accel_covariance

            # Write the Data
            # writer.writerow([time, wind_speed, wind_angle, battery_voltage, battery_current, '', pos_x, pos_y, pos_z, pos_covariance, '', orent_x, orent_y, orent_z, orent_w, '', '', linear_twist_x,
            #                 linear_twist_y, linear_twist_z, vel_covariance, '', angular_twist_x, angular_twist_y, angular_twist_z, '', linear_accel_x, linear_accel_y, linear_accel_z, acc_covariance])

            writer.writerow([time, wind_speed, wind_angle, battery_voltage, battery_current, '', pos_x, pos_y, pos_z, '', orent_x, orent_y, orent_z, orent_w, '', '', linear_twist_x,
                             linear_twist_y, linear_twist_z, '', angular_twist_x, angular_twist_y, angular_twist_z, '', linear_accel_x, linear_accel_y, linear_accel_z])


def sync_callback(wind, battery, imu, odom):
    """The callback for the ROS Time Synchronization Message Filter

    Arguments:
        wind {anemometer/Anemometer} -- The message data of the wind sensor
        battery {sensor_msgs/BatteryState} -- The message data of the battery
        imu {sensor_msgs/Imu} -- The message data of the Imu data
        odom {nav_msgs/Odometry} -- The Odometry data
    """
    global first_stamp, first
    # Initialize a blank data object
    combinedData = CombinedData()

    # Populate the object with the data of the sensors
    combinedData.wind = wind
    combinedData.voltage = battery.voltage
    combinedData.current = battery.current
    combinedData.odom_position = odom.pose.pose.position
    combinedData.odom_position_covariance = odom.pose.covariance
    combinedData.odom_orientation = odom.pose.pose.orientation
    combinedData.odom_velocity = odom.twist.twist
    combinedData.odom_velocity_covariance = odom.twist.covariance
    combinedData.imu_linear_accel = imu.linear_acceleration
    combinedData.imu_linear_accel_covariance = imu.linear_acceleration_covariance

    # Set the timestamp of the Header and rosbag datarow
    ts = rospy.Time(secs=battery.header.stamp.secs,
                    nsecs=battery.header.stamp.nsecs)
    combinedData.header.stamp = ts

    # If this is the first entry, set the initial timestamp to be able to calculate differential timestamps
    if first:
        first_stamp = ts
        first = False

    # Write the data into the output bagfile
    bag.write("/combined", combinedData, ts)

    # Add the data to the rows to be written to the CSV file
    datarows.append(combinedData)


# Initialize the ROS node
rospy.init_node("combiner")

# Subscribe to all necessary ROS topics
wind_subscriber = Subscriber("/anemometer", Anemometer)
battery_subscriber = Subscriber("/battery", BatteryState)
imu_subscriber = Subscriber("/imu/data", Imu)
odom_subscriber = Subscriber("/nav/odom", Odometry)

# Initialize the Time Synchronizer. Queue Size: 5, Slop: 0.1
tss = ApproximateTimeSynchronizer(
    [wind_subscriber, battery_subscriber, imu_subscriber, odom_subscriber], 5, 0.1)

# Set the callback function for
tss.registerCallback(sync_callback)

# Add the write method to the pre shutdown tasks
rospy.client.on_shutdown(write_files)

# Let the script run freely
rospy.client.spin()
