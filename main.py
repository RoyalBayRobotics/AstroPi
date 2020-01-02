#!/usr/bin/env python

import os
import time
import logging
import logzero
from logzero import logger

from camera import Camera
from sensehat import Sensors

start_time = time.time()
path = os.path.dirname(os.path.realpath(__file__))

logfile = path + "/data01.csv"
file_logger = logzero.setup_logger(
        logfile=logfile,
        disableStderrLogger=True,
        formatter=logging.Formatter('%(message)s'))
is_empty_file = os.stat(logfile).st_size == 0

camera = Camera(path=path, min_interval=5)
sensors = Sensors(path=path)

while time.time() - start_time < 60 * 60 * 3: # TODO subtract away loop time
    data = sensors.get_data()
    data['brightness'] = camera.update()
    data['time'] = time.time()

    if is_empty_file:
        file_logger.info(','.join(data.keys()))
        is_empty_file = False

    file_logger.info(','.join(str(v) for v in data.values()))
