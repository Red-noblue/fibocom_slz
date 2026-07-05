#!/usr/bin/env python

import subprocess
import rospy
from sensor_msgs.msg import NavSatFix

flag = 0
def callback(data):
    global flag
    if (data.status.status==-1 and flag==0 )  :
        cmd = 'blink1-tool --red'
        subprocess.call(cmd.split())
        flag = 1
       
    if (data.status.status==1 and flag==1) :
        cmd = 'blink1-tool --green'
        flag = 0
        subprocess.call(cmd.split())
    

def monitor():
    rospy.init_node('monitor', anonymous=True)
    rospy.Subscriber("/gps/fix", NavSatFix, callback)
    rospy.spin()


if __name__ == '__main__':
        monitor()
