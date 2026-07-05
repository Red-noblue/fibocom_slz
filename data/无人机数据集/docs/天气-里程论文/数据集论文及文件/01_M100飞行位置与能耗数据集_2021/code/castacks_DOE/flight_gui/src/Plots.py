import os
import re
import matplotlib.pyplot as plt 
import math
import scipy.integrate
import numpy as np
import pandas as pd


def SavePlot(x,y,title,xLabel,yLabel,flight):
    plt.plot(x,y)
    plt.title(title)
    plt.xlabel(xLabel)
    plt.ylabel(yLabel)
    plt.savefig(title+"_"+str(flight)+".jpg")
    plt.clf()

def make_plots():
    mainpath = os.getcwd()
    datapath = mainpath+"/data"
    to_do=[]
    done=[]
    main=True
    for dir_name, subdir_list, file_list in os.walk(datapath+"/Plots/Altitude"):
        for f in file_list:
            regex_match = re.search("\d+", f)
            fnum = regex_match.group(0)
            done.append(fnum)
        break
    for dir_name, subdir_list, file_list in os.walk(datapath):
        if "Plots" in dir_name:
            continue
        if main:
            main=False
            for iter in range(len(subdir_list) -1, -1, -1):
                try:
                    float(subdir_list[iter])
                except ValueError:
                    del subdir_list[iter]
        else:
            regex_match = re.search("\d+", dir_name)
            fnum = regex_match.group(0)
            if fnum not in done:
                to_do.append(dir_name)
    for flight in to_do:
        regex_match = re.search("\d+", flight)
        fnum = regex_match.group(0)
        print("Rendering Plot for flight {}".format(fnum))
        os.chdir(flight)
        f = pd.read_csv("combined.csv")
        # Power 
        f["Power"] = f["battery_current"]*f["battery_voltage"]
        x = "time"
        y = "Power"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = x+" [s]"
        yLabel = y+" [W]"
        SaveFolder = y
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Wind Speed
        x = "time"
        y = "wind_speed"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = x+" [s]"
        yLabel = y+" [m/s]"
        SaveFolder = y
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Wind Angle
        x = "time"
        y = "wind_angle"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = x+" [s]"
        yLabel = y+" [deg]"
        SaveFolder = y
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Battery Voltage
        x = "time"
        y = "battery_voltage"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = x+" [s]"
        yLabel = y+" [V]"
        SaveFolder = y
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Battery Current
        x = "time"
        y = "battery_current"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = x+" [s]"
        yLabel = y+" [A]"
        SaveFolder = y
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # GPS 
        x = "x"
        y = "y"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = "Longitude"
        yLabel = "Latitude"
        SaveFolder = "GPS"
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Altitude
        x = "time"
        y = "z"
        title = y+" vs "+x+" - Flight "+str(fnum)
        xLabel = "time [s]"
        yLabel = "Altitude [m]"
        SaveFolder = "Altitude"
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], f[y], title, xLabel, yLabel, fnum)
        os.chdir(flight)
        # Angles 
        q0 = f["w"]
        q1 = f["x.1"]
        q2 = f['y.1']
        q3 = f['z.1']
        phi = (2*(q0*q1+q2*q3))/(1-2*((q1)**2-(q2)**2))
        theta = 2*(q0*q2-q3*q1)
        psi = (2*(q0*q3+q1*q2))/(1-2*((q2)**2-(q3)**2))
            # phi
        x = "time"
        y = phi
        title = "phi vs "+x+" - Flight "+str(fnum)
        xLabel = "time [s]"
        yLabel = "phi [deg]"
        SaveFolder = "phi"
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], y, title, xLabel, yLabel, fnum)
        os.chdir(flight)
            # theta
        x = "time"
        y = theta
        title = "theta vs "+x+" - Flight "+str(fnum)
        xLabel = "time [s]"
        yLabel = "theta [deg]"
        SaveFolder = "theta"
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], y, title, xLabel, yLabel, fnum)
        os.chdir(flight)
            # psi
        x = "time"
        y = psi
        title = "psi vs "+x+" - Flight "+str(fnum)
        xLabel = "time [s]"
        yLabel = "psi [deg]"
        SaveFolder = "psi"
        try:
            os.chdir(datapath+"/Plots/"+SaveFolder)
        except:
            os.makedirs(datapath+"/Plots/"+SaveFolder)
            os.chdir(datapath+"/Plots/"+SaveFolder)
        os.chdir(datapath+"/Plots/"+SaveFolder)
        SavePlot(f[x], y, title, xLabel, yLabel, fnum)
        os.chdir(flight)


if __name__ == "__main__":
    make_plots()