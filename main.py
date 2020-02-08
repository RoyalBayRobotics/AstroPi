#!/usr/bin/env python

# imports
import os
import time
import contextlib
import csv

import logging
import logzero
from logzero import logger

from sensors import Sensors, Camera
from bittest import MemoryTest

# time keeping variables
MAX_RUN_TIME = 60 * 60 * 3 # seconds TODO remember to change it to 3 hours
start_time = time.time()
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
img_file = path + '/image{}.jpg' # gets formatted when saving
data_paths = [path + '/' + name for name in ('data01.csv', 'data02.csv')]
log_path = path + '/data{:02d}.log'.format(len(data_paths)+1)
elapsed_path = path + '/elasped_time'

# global variables
data_empty = [True] * len(data_paths)
data_writers = [None] * len(data_paths)
data_files = [None] * len(data_paths)

def log_data(data, n):
    global data_empty, data_writers

    # write CSV keys to file if it's empty
    if not data_writers[n]:
        data_writers[n] = csv.DictWriter(data_files[n], data.keys())
        if data_empty[n]:
            data_writers[n].writeheader()
            data_empty[n] = False

    # write datas to file
    data_writers[n].writerow(data)
    data_files[n].flush()

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
        rst = None
        for rst in memtest.test():
            if type(rst) is dict: break
            logger.debug("Memory test progress: %d%%", rst * 100)
            yield

        if rst != None:
            data = {'time': time.time()}
            data.update(rst)
            log_data(data, 1)

        yield

def main():
    global last_run_time, data_writers, data_empty

    # setup general logging
    logzero.logfile(log_path)
    #logzero.loglevel(logging.INFO)

    logger.info("Initializing")

    with contextlib.ExitStack() as stack:
        # CSV writers
        for i,path in enumerate(data_paths):
            data_files[i] = stack.enter_context(open(path, 'a'))
            data_empty[i] = os.stat(data_paths[i]).st_size == 0

        # elapsed time keeper
        elapsed_file = stack.enter_context(os.fdopen(os.open(elapsed_path, os.O_RDWR | os.O_CREAT | os.O_SYNC, 0o644), 'r+'))

        # figure out how much runtime there is left
        if os.stat(elapsed_path).st_size > 0:
            try:
                last_run_time = float(elapsed_file.read())
            except ValueError:
                logger.warning("Cannot obtain elasped time")

        if last_run_time > 0:
            logger.info("Already run for: %.1fs", last_run_time)

        # create tasks
        tasks = [ # (task, runs per iteration)
            (gen_task_sensors(), 1),
            (gen_task_memory_test(), 1),
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

            # save elapsed time in file so we know how much time we've left in case of SEU
            elapsed_file.seek(0)
            elapsed_file.write('{:=010.1f}'.format(now - start_time + last_run_time))
            elapsed_file.truncate()
            elapsed_file.flush()

            logger.debug("Time taken in loop: %fs", time.time() - now)

        logger.info("Ending program")

        # finished normally, remove elapsed time file
        try:
            os.remove(elapsed_path)
        except OSError as e:
            logger.warning('Cannot remove %s: %s', elapsed_path, str(e))

if __name__ == "__main__":
    main()
