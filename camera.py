#!/usr/bin/env python

from time import sleep
from picamera import PiCamera
from picamera.array import PiRGBArray
import numpy as np

camera = PiCamera()
output = PiRGBArray(camera)

for _ in camera.capture_continuous(output, 'rgb'):
    brightness = np.average(np.sum(output.array, axis=2))
    gain = camera.analog_gain * camera.digital_gain * camera.exposure_speed / (1000000 / camera.framerate)

    print(brightness / float(gain))

    output.truncate(0)
