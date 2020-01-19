#!/usr/bin/env python

from logzero import logger
import time

from picamera import PiCamera
from picamera.array import PiRGBArray
from PIL import Image

import numpy as np

class Camera:
    def __init__(self, path, min_interval=60):
        self.path = path
        self.min_interval = min_interval

        self.img_count = 0
        self.last_save_time = 0

        self.camera = PiCamera()
        self.output = PiRGBArray(self.camera)
        self.last = np.array([0, 0, 0])
        self.cam_iter = self.camera.capture_continuous(self.output, 'rgb')

    def update(self):
        next(self.cam_iter)

        colors = np.average(self.output.array, axis=(0,1))
        gain = self.camera.analog_gain * self.camera.digital_gain * self.camera.exposure_speed / (1000000 / self.camera.framerate)
        brightness = np.average(colors) / float(gain)

        now = time.time()
        if now - self.last_save_time > self.min_interval:
            #logger.info("Saving image")
            self.last = colors
            self.last_save_time = now
            img = Image.fromarray(self.output.array)
            img.save(self.path + "/image{}.jpg".format(self.img_count))
            self.img_count += 1

        self.output.truncate(0)

        return brightness
