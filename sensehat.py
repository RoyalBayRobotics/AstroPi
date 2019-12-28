#!/usr/bin/env python

import math
from sense_hat import SenseHat
from time import sleep

def length(v):
    return math.sqrt(v['x']**2 + v['y']**2 + v['z']**2)

sense = SenseHat()
sense.clear()
sense.set_imu_config(True, True, True)

while True:
    humidity = sense.get_humidity()
    temp = sense.get_temperature()
    pressure = sense.get_pressure()

    mag = length(sense.get_compass_raw())
    gyro = length(sense.get_gyroscope_raw())
    accel = length(sense.get_accelerometer_raw())

    print("humidity: {humidity}\ntemp: {temp}\npressure: {pressure}\nmag: {mag}\ngyro {gyro}\naccel {accel}\n"
            .format(humidity=humidity, temp=temp, pressure=pressure, mag=mag, gyro=gyro, accel=accel))
    sleep(1)
