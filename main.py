#!/usr/bin/env python

# imports
import os
import time

import logging
import logzero
from logzero import logger

from sensors import Sensors, Camera
from bittest import MemoryTest, FileTest

# time keeping variables
MAX_RUN_TIME = 10 # seconds TODO remember to change it to 3 hours
start_time = time.time()
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
data_file = path + '/data01.csv'
log_file = path + '/data02.log'
img_file = path + '/image{}.jpg'

def main():
    global last_run_time

    # save program output
    logzero.logfile(log_file)

    logger.info("Initializing")

    # logger for logging sensor datas
    file_logger = logzero.setup_logger(logfile=data_file, disableStderrLogger=True,
            formatter=logging.Formatter('%(message)s', datefmt='%s'))

    is_empty_file = os.stat(data_file).st_size == 0

    # figure out how much runtime there is left
    if is_empty_file: # first start, record initial start time
        file_logger.info(time.time())

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
    camera = Camera(img_file, min_interval=1) # TODO remember to change it to 1 minute
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
            data = {'time': time.time()}
            data.update(sensors.get_data())
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
