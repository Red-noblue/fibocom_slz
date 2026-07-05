#!/usr/bin/env python

import serial
import rospy
from anemometer.msg import Anemometer
from time import sleep

ser = serial.Serial('/dev/ttyUSB0',timeout=0.5)
ser.baudrate = 9600



def run():
    pub = rospy.Publisher('anemometer', Anemometer,queue_size=10)
    rospy.init_node('anemometer', anonymous=True)
    r = rospy.Rate(10) #10hz
    inp = '$01,WV?*//\r\n'
    msg = Anemometer()
    print('Getting data from wind sensor...')
 
    while not rospy.is_shutdown():
        #print('send')
        try:
            ser.write(inp)
            msg.header.stamp = rospy.Time.now()
            #r.sleep()
            out = ser.readline()
            #print(out[14:17],out)
            msg.speed = float(out[8:13])
            msg.angle = float(out[14:17])
        except serial.serialutil.SerialException:
            print('Could not parse')
            ser.close()
            #rospy.sleep(2)
            while True: 
                try:
                    ser.open()
                except:
                    continue
                break
            #rospy.loginfo(msg)
        pub.publish(msg)
        r.sleep()





if __name__ == '__main__':
    try:
        run()
    except rospy.ROSInterruptException: pass

