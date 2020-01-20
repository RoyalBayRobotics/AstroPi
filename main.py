#!/usr/bin/env python

# TODO list
# file error check
# memory error check

# TLE
name = 'SS (ZARYA)'
line1 = '1 25544U 98067A   19362.71902896  .00001053  00000-0  26848-4 0  9994'
line2 = '2 25544  51.6443 116.9397 0005193  79.2376  62.1357 15.49524693205439'

# imports
import os
import time
from collections import OrderedDict
import numpy as np
import ephem

import logging
import logzero
from logzero import logger

from sense_hat import SenseHat
from picamera import PiCamera
from picamera.array import PiRGBArray

from PIL import Image
import piexif
from piexif import GPSIFD

# time keeping variables
MAX_RUN_TIME = 10 # seconds
start_time = time.time()
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
log_file = path + '/data01.csv'
img_file = path + '/image{}.jpg'

# class for initializing and getting sensor data
class Sensors:
    def __init__(self):
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

# class for initiailzing camera, saving pictures, and getting brightness + location
class Camera:
    def __init__(self, min_interval=60):
        self.min_interval = min_interval

        self.img_count = 0
        self.last_save_time = 0

        # camera settings
        self.camera = PiCamera()
        self.output = PiRGBArray(self.camera)
        self.cam_iter = self.camera.capture_continuous(self.output, 'rgb')

        # set up location
        self.location = ephem.readtle(name, line1, line2)

    def update(self):
        next(self.cam_iter)

        # get current location
        self.location.compute()

        colors = np.average(self.output.array, axis=(0,1))
        gain = self.camera.analog_gain * self.camera.digital_gain * self.camera.exposure_speed / (1000000 / self.camera.framerate)
        brightness = np.average(colors) / float(gain)

        now = time.time()
        if now - self.last_save_time > self.min_interval:
            #logger.info("Saving image")
            self.last_save_time = now
            img = Image.fromarray(self.output.array)
            img.save(img_file.format(self.img_count), exif=self._location_tags())
            self.img_count += 1

        self.output.truncate(0)

        return {
            'brightness': brightness,
            'lat': str(self.location.sublat),
            'long': str(self.location.sublong),
        }

    def _location_tags(self):
        # split location into degrees, minutes, seconds
        lat = str(self.location.sublat).split(':')
        lon = str(self.location.sublong).split(':')

        # convert them to numbers
        lat = [int(lat[0]), int(lat[1]), int(float(lat[2]) * 10)]
        lon = [int(lon[0]), int(lon[1]), int(float(lon[2]) * 10)]

        # get reference direction
        lat_ref = 'S' if lat[0] < 0 else 'N'
        lon_ref = 'W' if lon[0] < 0 else 'E'

        lat[0] = abs(lat[0])
        lon[0] = abs(lon[0])

        # create exif data
        exif_data = {
            'GPS': {
                GPSIFD.GPSLatitudeRef: lat_ref,
                GPSIFD.GPSLatitude: ((lat[0], 1), (lat[1], 1), (lat[2], 10)),
                GPSIFD.GPSLongitudeRef: lon_ref,
                GPSIFD.GPSLongitude: ((lon[0], 1), (lon[1], 1), (lon[2], 10)),
            }
        }

        return piexif.dump(exif_data)

def main():
    global last_run_time

    logger.info("Initializing")

    # logger for logging sensor datas
    file_logger = logzero.setup_logger(logfile=log_file, disableStderrLogger=True,
            formatter=logging.Formatter('%(asctime)s,%(message)s', datefmt='%s'))

    is_empty_file = os.stat(log_file).st_size == 0

    if is_empty_file: # record initial start time
        file_logger.info("")

    else: # read the previous runtime
        with open(log_file, 'rb') as file:
            # start time
            start = file.readline().decode().split(',')[0]

            # seek backwards until EOL
            if start.isdigit():
                try:
                    file.seek(-2, os.SEEK_END)
                    while file.read(1) != b"\n":
                        file.seek(-2, os.SEEK_CUR)

                    end = file.readline().decode().split(',')[0]

                    if end.isdigit():
                        # save the run time of last execution if there was one
                        last_run_time = int(end) - int(start)

                except OSError:
                    pass

    # init camera and sensors
    camera = Camera(min_interval=60)
    sensors = Sensors()

    logger.info("Running")

    last_time = 0
    while True:
        now = time.time()

        # check runtime
        if now - start_time + last_run_time > MAX_RUN_TIME: break # TODO account for loop execution time

        # limit execution rate to 1/sec
        if now - last_time < 1:
            time.sleep(1 - (now-last_time))
            continue
        last_time = now

        # get datas
        data = sensors.get_data()
        data.update(camera.update())
        data.update({'time': time.time()})

        # write CSV keys to file when it's empty
        if is_empty_file:
            file_logger.info(','.join(data.keys()))
            is_empty_file = False

        # write datas to file
        file_logger.info(','.join(str(v) for v in data.values()))

    logger.info("Ending program")

if __name__ == "__main__":
    main()
