#!/usr/bin/env python
"""ROS Node which communicates with an BME280 environmental data sensor via I2C
to publish it's readings on a topic

Bastian Wagner
Carnegie Mellon University - June 2019
"""
import rospy
import smbus2
import bme280
from environmental_sensor.msg import EnvironmentalData

##########################################
# I2C Communication Parameters
# Set according to your setup
# (TODO: Set Values as program parameters)
##########################################
PORT = 1
ADDRESS = 0x77


def environment_sensor():
    """Initialize the connection and publish new data as long as ROS is running
    """
    # Init Connection
    bus = smbus2.SMBus(PORT)
    calibration_params = bme280.load_calibration_params(bus, ADDRESS)
    # Set-Up ROS Node and Topic
    rospy.init_node('environmental_sensor', anonymous=True)
    pub = rospy.Publisher('environmental_data', EnvironmentalData, queue_size=100)
    rate = rospy.Rate(10)
    print("Starting Environmental readings....")
    while not rospy.is_shutdown():
        # Read data
        data = bme280.sample(bus, ADDRESS, calibration_params)
        # Construct the message with the data
        msg = EnvironmentalData()
        msg.header.stamp = rospy.Time.now()
        msg.temperature = data.temperature
        msg.pressure = data.pressure
        msg.humidity = data.humidity
        pub.publish(msg)
        rate.sleep()


if __name__ == '__main__':
    try:
        environment_sensor()
    except rospy.ROSInterruptException:
        print('Exited')
