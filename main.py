#!/usr/bin/env python

# imports
import os
import time

import logging
import logzero
from logzero import logger

from sensors import Sensors, Camera
from bittest import MemoryTest, FileTest

# global variables
num_datas = 3
data_empty = [True] * num_datas
data_loggers = [None] * num_datas

# time keeping variables
MAX_RUN_TIME = 60 # seconds TODO remember to change it to 3 hours
start_time = time.time()
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
img_file = path + '/image{}.jpg' # gets formatted when saving
data_files = [path + '/data{:02d}.csv'.format(n+1) for n in range(num_datas)]
log_file = path + '/data{:02d}.log'.format(num_datas+1)

def log_data(data, n):
    global data_empty

    # write CSV keys to file if it's empty
    if data_empty[n]:
        data_loggers[n].info(','.join(data.keys()))
        data_empty[n] = False

    # write datas to file
    data_loggers[n].info(','.join(str(v) for v in data.values()))

def gen_task_sensors():
    camera = Camera(img_file, min_interval=60)
    sensors = Sensors()

    last_time = 0
    while True:
        now = time.time()

        # limit execution rate to 1/sec
        if now - last_time < 1:
            yield

        # record results
        data = {'time': time.time()}
        data.update(sensors.get_data())
        data.update(camera.update())

        log_data(data, 0)

        last_time = now
        yield

def gen_task_memory_test():
    memtest = MemoryTest(batch_size=1024*1024*50)

    # initial checksum for memory is fast enough to do it all at once
    for rst in memtest.update_hash():
        logger.debug("Memory checksum progress: %d%%", rst * 100)

    yield

    while True:
        for rst in memtest.test():
            if type(rst) is dict: break
            logger.debug("Memory test progress: %d%%", rst * 100)
            yield

        data = {'time': time.time()}
        data.update(rst)
        log_data(data, 1)

def gen_task_file_test():
    with FileTest(path) as filetest:

        # calculate initial checksum
        for rst in filetest.update_hash():
            logger.debug("File checksum progress: %d%%", rst * 100)
            yield

        while True:
            for rst in filetest.test():
                if type(rst) is dict: break
                logger.debug("File test progress: %d%%", rst * 100)
                yield

            data = {'time': time.time()}
            data.update(rst)
            log_data(data, 2)

def main():
    global last_run_time, data_loggers, data_empty

    # setup general logging
    logzero.logfile(log_file)

    logger.info("Initializing")

    # logger for datas
    formatter=logging.Formatter('%(message)s', datefmt='%s')
    for i in range(num_datas):
        data_loggers[i] = logzero.setup_logger(name=str(i), logfile=data_files[i], disableStderrLogger=True, formatter=formatter)
        data_empty[i] = os.stat(data_files[i]).st_size == 0

    # figure out how much runtime there is left using one of the data files
    if data_empty[0]: # fresh start, record start time
        data_loggers[0].info(time.time())

    else: # not fresh start, read the previous runtime
        with open(data_files[0], 'rb') as file:
            # start time
            start = file.readline().decode()

            # seek backwards until EOL
            try:
                file.seek(-2, os.SEEK_END)
                while file.read(1) != b"\n":
                    file.seek(-2, os.SEEK_CUR)

                end = file.readline().decode().split(',')[0]

                # save the run time of last execution if there was one
                last_run_time = float(end) - float(start)

            except (OSError, ValueError):
                logger.warning("Cannot obtain last run time")
                pass

    if last_run_time > 0:
        logger.info("Already run for: %fs", last_run_time)

    # create tasks
    tasks = [ # (task, runs per iteration)
        (gen_task_sensors(), 1),
        (gen_task_memory_test(), 1),
        (gen_task_file_test(), 50)
    ]

    logger.info("Running")

    while True:
        now = time.time()

        # check runtime
        if now - start_time + last_run_time > MAX_RUN_TIME: # TODO account for loop execution time
            break

        # execute the tasks
        for task in tasks:
            try:
                for i in range(task[1]):
                    next(task[0])
            except StopIteration:
                logger.warning("%s ended early", task.__name__)
                tasks.remove(task)

        logger.debug("Time taken in loop: %fs", time.time() - now)

    logger.info("Ending program")

if __name__ == "__main__":
    main()
