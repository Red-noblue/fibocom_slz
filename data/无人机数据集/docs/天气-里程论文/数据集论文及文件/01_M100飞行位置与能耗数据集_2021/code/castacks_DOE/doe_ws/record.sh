#!/bin/bash
################################################
# Script to start the recording of test data
# This script takes 1 positional argument, namely if it is running on an UAV or UGV
# Default mode is UAV, UGV ground mode is enabled by passing "ground" as argument
# 
# Bastian Wagner, Jay Patrikar, Vaibhav Arcot
# Carnegie Mellon University - 2019
################################################

blink1-tool --red > /dev/null

# Get the number of the next test by looking for the last number and adding 1
name=$(($(ls data | sort -g | tail -n 1 | grep -Eo "[0-9]+") + 1))

testname="flight"
if [ $1 = "ground" ];
then
	testname="drive"
fi

echo "Starting sequence for" "$testname" "$name"
trap "" HUP

# Check that ROS is running by waiting for the rostopic list command to successfully run
echo "Waiting for ROS"
until $(rostopic list > /dev/null 2>&1) ; do sleep 1; done
echo "ROS started"

# Set the variables needed to check the status with respect to the type of drone
b=8

# If in ground mode, check for 1 more topic
if [ $1 = "ground" ];
then
	b=$(($b+1))
fi

fix=1
recording=0

# Do infinitely to ensure execution
while true;
do
	# Check if all ROS Topics are being published
	if [ $(rostopic list | wc -l) = $b ];
	then
		# If a GPS Fix has been obtained start the recording
		if [ $fix -eq 0 ];
		then
			# If not recording yet, start the recording
			if [ $recording -eq 0 ];
			then
				blink1-tool --blue
				echo "GPS Status OK"
				echo "Starting to record"

				# Set the topics according to current mode
				topiclist="/anemometer /battery /nav/odom /imu/data"
				if [ $1 = "ground" ];
				then
					topiclist="/battery /battery2 /environmental_data /nav/odom /imu/data"
				fi
				# Start the recording of the ROSbag and save the PID to be able to exit the program after loss of connection
				rosbag record -O /home/pi/data/"$name" $(echo $topiclist) __name:=my_bag > record.log 2>&1 &
				echo $! > save_pid.txt

				# Wait until recording node shows up
				until $(rosnode list | grep my_bag > /dev/null 2>&1) ; do sleep 1; done
				echo "Recording started"
				blink1-tool --green > /dev/null

				# Set the recording status to 1
				recording=1
			fi
			blink1-tool --green > /dev/null
		else
			echo "Checking GPS Status"
			# Check the GPS Status by looking for the status line in /gps/fix
			rostopic echo -n 1 /gps/fix | grep 'status: 30' > /dev/null 2>&1
			fix=$?
			blink1-tool --red > /dev/null
		fi
	else
		blink1-tool --red > /dev/null
	fi
done
trap - HUP
