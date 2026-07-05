# ROS Time Synchronizer
This ROS Package provides a script to synchronize multiple topics in a rosbag file into one single output message and save the output into a new rosbag and CSV-file. Note: The program will replay the bagfile at 10x the recording speed. This value can be changed by passing the ```rate``` parameter to ```roslaunch```
## Installation
1. Clone this package into the ```src``` folder of a catkin workspace (preferably the one including the ```anemometer/Anemometer``` message)
2. Run ```catkin build``` in the root directory of the workspace
3. Run ```source devel/setup.bash``` in the root directory of the workspace
## Usage
The package includes a launch file automatically running the synchronization. To run it onto a file use the following command:  
```roslaunch filtering convert.launch file:={PATH_TO_BAGFILE} outpath:={OUTPUT_FILE_PATH}```  
If you are already in the directory containing the bagfile you can also run  
```roslaunch filtering convert.launch file:=$(realpath BAGFILE_NAME) outpath:=$(realpath .)```  
This will run the script on the bagfile specified and save the output contents into the current directory
## Usage with multiple files
To run the script on all bagfiles in a directory run the ```do_all.sh``` Bash script in the directory containing the files. The output files for each bagfile will be generated into a corresponding subfolder.