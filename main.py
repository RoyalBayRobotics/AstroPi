#!/usr/bin/env python

# TODO list
# file error check
# memory error check

# TLE
name = 'ISS (ZARYA)'
line1 = '1 25544U 98067A   20033.56530057  .00002248  00000-0  48744-4 0  9996'
line2 = '2 25544  51.6429 299.5086 0005402 222.1202 199.9632 15.49136719210996'

# imports
import os
import time
import numpy as np
import ephem

import logging
import logzero
from logzero import logger

from sense_hat import SenseHat
from picamera import PiCamera

from memorytest import MemoryTest
from filetest import FileTest

# time keeping variables
MAX_RUN_TIME = 10 # seconds TODO remember to change it to 3 hours
start_time = time.time()
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
data_file = path + '/data01.csv'
log_file = path + '/data02.log'
img_file = path + '/image{}.jpg'

# class for initializing and getting sensor data
class Sensors:
    def __init__(self):
        self.sense = SenseHat()
        self.sense.clear()
        self.sense.set_imu_config(True, True, True)

    def get_data(self):
        data = {
            "humidity": self.sense.get_humidity(),
            "temp": self.sense.get_temperature(),
            "pressure": self.sense.get_pressure(),
        }

        mag = self.sense.get_compass_raw()
        gyro = self.sense.get_gyroscope_raw()
        accel = self.sense.get_accelerometer_raw()

        data['mag_x'] = mag['x']; data['mag_y'] = mag['y']; data['mag_z'] = mag['z']
        data['gyro_x'] = gyro['x']; data['gyro_y'] = gyro['y']; data['gyro_z'] = gyro['z']
        data['accel_x'] = accel['x']; data['accel_y'] = accel['y']; data['accel_z'] = accel['z']

        return data

# class for initiailzing camera, saving pictures, and getting picture's information
class Camera:
    def __init__(self, min_interval=60):
        self.min_interval = min_interval

        self.img_count = -1
        self.last_save_time = 0

        # camera settings
        self.camera = PiCamera()

        # set up location
        self.location = ephem.readtle(name, line1, line2)

    def update(self):
        # get current location
        self.location.compute()

        picture_taken = False
        now = time.time()

        # Take picture every `min_interval` time
        if now - self.last_save_time > self.min_interval:
            #logger.info("Saving image")
            self.last_save_time = now
            self.img_count += 1
            self._update_location()
            self.camera.capture(img_file.format(self.img_count))
            picture_taken = True

        return {
            'gain': self.camera.analog_gain * self.camera.digital_gain,
            'exposure': self.camera.exposure_speed,
            'lat': str(self.location.sublat),
            'long': str(self.location.sublong),
            'alt': self.location.elevation,
            'picture_number': -1 if not picture_taken else self.img_count,
        }

    def _update_location(self):
        # split location into degrees, minutes, seconds
        lat = str(self.location.sublat).split(':')
        lon = str(self.location.sublong).split(':')

        # convert them to numbers
        lat = [int(lat[0]), int(lat[1]), int(float(lat[2]) * 10)]
        lon = [int(lon[0]), int(lon[1]), int(float(lon[2]) * 10)]

        # elevation
        alt = int(self.location.elevation * 10)

        # set reference direction
        lat_ref = 'S' if lat[0] < 0 else 'N'
        lon_ref = 'W' if lon[0] < 0 else 'E'

        lat[0] = abs(lat[0])
        lon[0] = abs(lon[0])

        # create exif data
        self.camera.exif_tags['GPS.GPSLatitudeRef'] = lat_ref
        self.camera.exif_tags['GPS.GPSLongitudeRef'] = lon_ref
        self.camera.exif_tags['GPS.GPSAltitudeRef'] = '0'
        self.camera.exif_tags['GPS.GPSLatitude'] = '{}/1,{}/1,{}/10'.format(*lat)
        self.camera.exif_tags['GPS.GPSLongitude'] = '{}/1,{}/1,{}/10'.format(*lon)
        self.camera.exif_tags['GPS.GPSAltitude'] = '{}/10'.format(alt)

def main():
    global last_run_time

    # save program output
    logzero.logfile(log_file)

    logger.info("Initializing")

    # logger for logging sensor datas
    file_logger = logzero.setup_logger(logfile=data_file, disableStderrLogger=True,
            formatter=logging.Formatter('%(asctime)s,%(message)s', datefmt='%s'))

    is_empty_file = os.stat(data_file).st_size == 0

    # figure out how much runtime there is left
    if is_empty_file: # first start, record initial start time
        file_logger.info("")

    else: # not first start, read the previous runtime
        with open(data_file, 'rb') as file:
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
    camera = Camera(min_interval=1) # TODO remember to change it to 1 minute
    sensors = Sensors()
    memTest = MemoryTest()
    fileTest_ = FileTest(path)

    with fileTest_ as fileTest:
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
            data.update(memTest.test())
            data.update(fileTest.test())

            # write CSV keys to file when it's empty
            if is_empty_file:
                file_logger.info(','.join(data.keys()))
                is_empty_file = False

            # write datas to file
            file_logger.info(','.join(str(v) for v in data.values()))

            logger.info("Time taken in loop: %fs", time.time() - now)

    logger.info("Ending program")

if __name__ == "__main__":
    main()
