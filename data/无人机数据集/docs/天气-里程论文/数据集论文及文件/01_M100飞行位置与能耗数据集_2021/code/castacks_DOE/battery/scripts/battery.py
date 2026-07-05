#!/usr/bin/env python
"""Node to read battery data from the ADS1x15 sensor

Jay Patrikar
Carnegie Mellon University - February 2019
"""
import os
import rospy
from sensor_msgs.msg import BatteryState
import Adafruit_ADS1x15

# Initialize publishers and constants for reading
pub = rospy.Publisher('battery', BatteryState, queue_size=100)
pub2 = rospy.Publisher('battery2', BatteryState, queue_size=100)
adc = Adafruit_ADS1x15.ADS1115()
GAIN = 1


def read_and_publish(second=False):
    """Read the data from the sensor and publish it

    Keyword Arguments:
        second {bool} -- Read the second sensor? (default: {False})
    """
    # Get the index of the currently read sensor (0/1 for the first 2/3 for the second)
    index_volt = 0 + 2*second
    index_curr = 1 + 2*second

    # Read the voltage and current from the sensor
    volt = (adc.read_adc(0, gain=GAIN)/32767.0)*4.096*10.0161
    curr = (adc.read_adc(1, gain=GAIN)/32767.0)*4.096*63.61225

    # Construct the message
    msg = BatteryState()
    msg.header.stamp = rospy.Time.now()
    msg.voltage = volt
    msg.current = curr

    # Publish on the corresponding topic
    if not second:
        pub.publish(msg)
    else:
        pub2.publish(msg)


def battery():
    """Inizialize and run the node while ROS is alive
    """
    # Check the environment variable on whether there are two battery sensor readings
    is_dual_battery = os.environ["SYSTEM_BATTERY_INFO"] == "DUAL"
    if is_dual_battery:
        print("Running in dual battery mode")
    rospy.init_node('battery', anonymous=True)
    rate = rospy.Rate(10)
    print('Starting Battery Readings....')
    while not rospy.is_shutdown():
        # Read the data for the first values
        read_and_publish()

        # If there is a second reading, read those values too
        if is_dual_battery:
            read_and_publish(second=True)
        rate.sleep()


if __name__ == '__main__':
    try:

        battery()
    except rospy.ROSInterruptException:
        print('Exited')
