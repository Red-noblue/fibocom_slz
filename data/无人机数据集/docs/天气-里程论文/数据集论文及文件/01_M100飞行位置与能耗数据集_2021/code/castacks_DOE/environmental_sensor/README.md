# Environmental Sensor
This package includes a node and message to publish data from an environmental sensor such as the [BME280](https://www.adafruit.com/product/2652) on an Raspberry Pi.  
The provided python node reads the Data of an BME280 connected via I2C at the given address, in future versions it is planned to add this address as a startup parameter.

## Dependencies
This package depends on [RPi.bme280](https://pypi.org/project/RPi.bme280/)  
```pip install RPi.bme280```  

## Installation
Clone this package into your workspace and build