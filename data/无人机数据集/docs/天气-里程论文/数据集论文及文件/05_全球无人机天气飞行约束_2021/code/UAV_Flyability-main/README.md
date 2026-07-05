# UAV Flyability

### Overview 
This documnetiation is designed to be a technical document with relation to the example of calculating drone flyability by using grided weather data.

<b>Weather constraints on global drone flyability</b>
<br>Small aerial drones are used in a growing number of commercial applications. 3 However, drones cannot fly in all weather, which impacts their reliability for time-sensitive 4 operations. We explore the impact of weather on global drone flyability by comparing historical 5 wind speed, temperature, and precipitation data to manufacturer-reported thresholds of 6 common commercial and weather-resistant drones. We show that global flyability is highest in 7 warm and dry continental regions and lowest over oceans and at high latitudes. Median global 8 flyability for common drones is low: 5.7 hrs/day or 2.0 hrs/day if restricted to daylight hours. 9 Weather-resistant drones have higher flyability (20.4 and 12.3 hrs/day, respectively). These 10 estimates do not consider other weather conditions impacting safe drone operations. An 11 inverse analysis for major population centres shows the largest flyability gains for common 12 drones can be achieved by increasing maximum wind speed and precipitation thresholds from 13 10 to 15 m/s and 0 to 1 mm/hr, respectively.
<br> The corresponding peer-reviewed journal artical can be found here: https://doi.org/10.1038/s41598-021-91325-w


### Required libraries 
- <a href= "https://unidata.github.io/netcdf4-python/netCDF4/index.html"> netCDF4 </a>: read and write netCDF4 file 
- <a href= "https://numpy.org/"> numpy </a>: core library for array-based calculation
- <a href= "https://rhodesmill.org/pyephem/"> ephem </a>: calculate daylights 
- <a href= "https://matplotlib.org/"> matplotlib </a>: core library for visualization 
- <a href= "https://matplotlib.org/basemap/"> basemap </a>: plot 2D data on maps in python 


### Optional libraries
- <a href= "https://cds.climate.copernicus.eu/api-how-to"> cdsapi </a>: download ERA5 data

### Scripts 
This folder contains two scripts to help you understand how to calculate drone flyability. 
<br> <b> Download ERA5.ipynb </b> shows an example of downloading ERA5 data by using cdsapi.
<br> <b> Drone flyability calculation.ipynb </b> shows an examples of calculating monthly drone flyability (both day and night and daylight only) for Alberta in June, 2019.  
 
### Sample data
<b> sampledata_06_2019.nc </b> was downloaded by using script <b> Download ERA5.ipynb </b>. Please also download this data if you wanted to run <b> Drone flyability calculation.ipynb </b> and to generate the exact results.

### Results of Gao et al., submitted can be found in MS_results folder

### Sample results 
https://github.com/MozhouGao/UAV_Flyability/blob/main/Fig1.png?raw=true
 
### Contact 
Please feel free to contact me if you need any further information! 
<br> mozhou.gao@ucalgary.ca
