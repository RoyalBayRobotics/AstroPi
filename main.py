#!/usr/bin/env python

# TODO list
# camera location data
# file error check
# memory error check

import os
import time
import logging
import logzero
from logzero import logger

from camera import Camera
from sensehat import Sensors

MAX_RUN_TIME = 10

start_time = time.time()

# used when the first run got interrupted
last_start_time = last_end_time = start_time

path = os.path.dirname(os.path.realpath(__file__))
logfile = path + "/data01.csv"

def main():
    global last_start_time
    global last_end_time

    # logger for logging sensor datas
    file_logger = logzero.setup_logger(logfile=logfile, disableStderrLogger=True,
            formatter=logging.Formatter('%(asctime)s,%(message)s', datefmt='%s'))

    is_empty_file = os.stat(logfile).st_size == 0
    if not is_empty_file: # read the previous runtime
        with open(logfile, 'rb') as file:
            start = file.readline().decode().split(',')[0]

            # seek backwards until EOL
            file.seek(-2, 2)
            while file.read(1) != b"\n":
                file.seek(-2, 1)

            end = file.readline().decode().split(',')[0]

            if start.isdigit():
                last_start_time = int(start)
            if end.isdigit():
                last_end_time = int(end)

    # record initial start time
    if is_empty_file:
        file_logger.info("")

    # init camera and sensors
    camera = Camera(path=path, min_interval=60)
    sensors = Sensors(path=path)

    last_time = 0
    while True:
        now = time.time()

        # check runtime
        if now - start_time + last_end_time - last_start_time > MAX_RUN_TIME: break # TODO account for loop execution time

        # limit execution rate to 1/sec
        if now - last_time < 1: continue

        last_time = now

        data = sensors.get_data()
        data['brightness'] = camera.update()
        data['time'] = time.time()

        if is_empty_file:
            file_logger.info(','.join(data.keys()))
            is_empty_file = False

        file_logger.info(','.join(str(v) for v in data.values()))

    logger.info("Ending program")

if __name__ == "__main__":
    main()
