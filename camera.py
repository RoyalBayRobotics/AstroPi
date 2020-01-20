#!/usr/bin/env python

from logzero import logger
import time

from picamera import PiCamera
from picamera.array import PiRGBArray

from PIL import Image
import piexif
from piexif import GPSIFD

import numpy as np
import ephem

class Camera:
    def __init__(self, path, min_interval=60):
        self.path = path
        self.min_interval = min_interval

        self.img_count = 0
        self.last_save_time = 0

        # camera settings
        self.camera = PiCamera()
        self.output = PiRGBArray(self.camera)
        self.last = np.array([0, 0, 0])
        self.cam_iter = self.camera.capture_continuous(self.output, 'rgb')

        # set up location
        name = 'SS (ZARYA)'
        line1 = '1 25544U 98067A   19362.71902896  .00001053  00000-0  26848-4 0  9994'
        line2 = '2 25544  51.6443 116.9397 0005193  79.2376  62.1357 15.49524693205439'
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
            self.last = colors
            self.last_save_time = now
            img = Image.fromarray(self.output.array)
            img.save(self.path + "/image{}.jpg".format(self.img_count), exif=self._location_tags())
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
