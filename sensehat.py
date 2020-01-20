#!/usr/bin/env python

from collections import OrderedDict
from sense_hat import SenseHat

class Sensors:
    def __init__(self, path):
        self.sense = SenseHat()
        self.sense.clear()
        self.sense.set_imu_config(True, True, True)

    def get_data(self):
        data = OrderedDict({
            "humidity": self.sense.get_humidity(),
            "temp": self.sense.get_temperature(),
            "pressure": self.sense.get_pressure(),
        })

        mag = self.sense.get_compass_raw()
        gyro = self.sense.get_gyroscope_raw()
        accel = self.sense.get_accelerometer_raw()

        data['mag_x'] = mag['x']; data['mag_y'] = mag['y']; data['mag_z'] = mag['z']
        data['gyro_x'] = gyro['x']; data['gyro_y'] = gyro['y']; data['gyro_z'] = gyro['z']
        data['accel_x'] = accel['x']; data['accel_y'] = accel['y']; data['accel_z'] = accel['z']

        return data
