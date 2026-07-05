# DOE Project Flight GUI
Simple Graphical User Interface to control the flights.

# Setup
To use this program, ROS has to be installed and the ```doe_ws``` workspace has to be cloned.  
The Path to the workspace must be set in the settings (together with the connection details)

## Usage
1. Start the program by using the provided start script (```start.sh```)
2. Set the SSH parameters in the Settings (File->Settings->Save)
3. Connect to the drone's WIFI
4. Click "Connect"
5. Enter the altitude and speed in the respective field
6. The Current Flight number will be shown in the tetxtbox in the bottom left
7. After the drone has landed, click on "Read Data"
8. After a successful data transfer, click "Reset" and restart the drone

If, for any reason the program crashed during the flight or the WiFi lost connection to the drone use the "Read Data Manually" button after entering the current flight number in the textbox above it. It is only available when not connected to the system (WiFi must be connected).  
If the data could not be read, wait for at least 20s and try again.  
If the data could not be read again, the data has to be manually read.

Plots are automatically generated when the program is closed (Output in the terminal). Plots can also be generated manually by running the provided ```do_plots.sh``` script.

## Needed Packages
- PyQt5 ```pip3 install PyQt5```
- Parmiko ```pip3 install paramiko```
- bash ```pip3 install bash```
- pandas ```pip3 install pandas```
- matplotlib ```pip3 install matplotlib```
- scipy ```pip3 install scipy```
- numpy ```pip3 install numpy```

## Core Contributor

Bastian Wagner
## Core Contributor
Bastian Wagner

## Maintaner
Jay Patrikar (jaypat@cmu.edu)

### License ###
[This software is BSD licensed.](http://opensource.org/licenses/BSD-3-Clause)
 
Copyright (c) 2020, Carnegie Mellon University
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.