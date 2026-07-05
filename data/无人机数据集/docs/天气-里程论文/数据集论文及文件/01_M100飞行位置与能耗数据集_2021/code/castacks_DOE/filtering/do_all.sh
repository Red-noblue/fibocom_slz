#!/bin/bash
# Bash Script for running the ROS time synchronizer on all bagfiles in a given directory.
#
# Written by Bastian Wagner in April 2019 at Carnegie Mellon University's Air Lab

echo "Running the synchronizer for every new bagfile in the directory structure"
files=$(find . -maxdepth 1 -type d '!' -exec test -e "{}/combined.bag" ';' -print)
for filename in $files; do
	bagfilename=$filename"/raw.bag"
	if test -f $bagfilename; then
		echo "Running for directory $filename"
		roslaunch filtering convert.launch file:=$(realpath $bagfilename) outpath:=$(realpath $filename)
        	echo "Done Running for directory $filename"
	fi
done
echo "Done"
