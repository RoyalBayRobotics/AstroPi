#!/usr/bin/env python3
# Written by Rio Liu

# This is the main file of our experiment
#
# The goal of our experiment is to find out how much the cosmic rays and
# magnetic field in Earth's orbit affects an electronic device like RaspberryPi.
#
# There's two parts of this program. One of them is just a data logger, located
# in sensors.py. It records and all the sensor datas and pictures at an interval.
# Data saving code, except for pictures, is performed in main.py.
#
# The other part is memory testing, located in bittest.py. Its job is to
# continuously create a checksum of a large memory region and compare it to the
# previous result. If there's a difference, that means something has changed
# the memory.
#
# Additionally, this program can detect if it has ended uncleanly during the
# previous execution. Thus looking at the log, we can tell if an reset caused
# by SEU had happened.
#
# The code uses python's generator syntax to achieve multitasking without using
# threads. Long-running codes like performing memory checksum are broken into
# small batches and uses `yield` to give other tasks a chance to run. Although
# it might not utilize the CPU as good as using threads, it is easy to manage,
# and stopping the main thread stops everything. Plus AstroPi only has 1 cpu
# anyways, so there wouldn't be too much performance gained by using threading.

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
MAX_RUN_TIME = 60 * 60 * 3 - 5 # in seconds, has a margin of 5 seconds before MCP kills us
start_time = time.time() # records when the program started
last_run_time = 0 # used when the first run got interrupted

# file paths
path = os.path.dirname(os.path.realpath(__file__))
img_path = path + '/image{}.jpg' # gets formatted when saving
data_paths = [path + '/' + name for name in ('data01.csv', 'data02.csv')]
log_path = path + '/data{:02d}.log'.format(len(data_paths)+1)
elapsed_path = path + '/elasped_time' # used to record elapsed time in case of unexpected reset (SEU for example)

# global variables
data_empty = [True] * len(data_paths)
data_writers = [None] * len(data_paths)
data_files = [None] * len(data_paths)
elapsed_file = None

# this function logs data to a certain data file.
# it also creates CSV keys if the file is empty
def log_data(data, n):
    global data_empty, data_writers

    # create CSV writer
    if not data_writers[n]:
        data_writers[n] = csv.DictWriter(data_files[n], data.keys())

    # write CSV keys to file if it's empty
    if data_empty[n]:
        data_writers[n].writeheader()
        data_empty[n] = False

    # write datas to file
    data_writers[n].writerow(data)
    data_files[n].flush()

# === tasks ===

# this task writes the elasped execution time to a file
# which can be used in the case of an unexpected reset
def task_elapsed_time():
    last_time = 0
    while True:
        # limit execution rate to 1/sec
        while time.time() - last_time < 1:
            yield

        # write elapsed time to file
        elapsed_file.seek(0)
        elapsed_file.write('{:=010.1f}'.format(time.time() - start_time + last_run_time))
        elapsed_file.truncate()
        elapsed_file.flush()

        last_time = time.time()
        yield

# this task records sensor readouts every second, and takes picture every minute
def task_sensors():
    camera = Camera(img_path, min_interval=60)
    sensors = Sensors()

    last_time = 0
    while True:
        # limit execution rate to 1/sec
        while time.time() - last_time < 1:
            yield

        # record results
        data = {'time': time.time()}
        data.update(sensors.get_data())
        data.update(camera.update()) # camera.update() takes picture automatically

        log_data(data, 0)

        last_time = time.time()
        yield

# this task continuously test the memory to detect bit flips
# both test() and update_hash() function returns an generator
# so we can execute just a portion of them every loop
def task_memory_test():
    memtest = MemoryTest(batch_size=1024*1024*50)

    # update the initial memory checksum
    for rst in memtest.update_hash():
        logger.debug("Memory checksum progress: %d%%", rst * 100)
        yield

    while True:
        # check if memory is the same as previous run
        rst = None
        for rst in memtest.test():
            if type(rst) is dict: break # got a result
            logger.debug("Memory test progress: %d%%", rst * 100)
            yield

        # record the test result
        if rst != None:
            data = {'time': time.time()}
            data.update(rst)
            log_data(data, 1)

        yield

def main():
    global last_run_time, data_writers, data_empty, elapsed_file

    # setup program logging
    logzero.logfile(log_path)
    logzero.loglevel(logging.INFO)

    logger.info("Initializing")

    # setup for all the data and log files
    with contextlib.ExitStack() as stack:
        # CSV writers
        for i,path in enumerate(data_paths):
            data_files[i] = stack.enter_context(open(path, 'a'))
            data_empty[i] = os.stat(data_paths[i]).st_size == 0

        # elapsed time keeper
        # because this file is used to indicate unexpected reset, we need to make sure it's written directly to storage
        elapsed_file = stack.enter_context(os.fdopen(os.open(elapsed_path, os.O_RDWR | os.O_CREAT | os.O_SYNC, 0o644), 'r+'))

        # if there's data in the elapsed time file, that means the program didn't finish normally last time
        # figure out how much runtime there is left
        if os.stat(elapsed_path).st_size > 0:
            logger.info("Last execution ended unexpectedlly")
            try:
                last_run_time = float(elapsed_file.read())
            except ValueError:
                logger.warning("Cannot obtain elasped time")

        if last_run_time > 0:
            logger.info("Already run for: %.1fs", last_run_time)

        # create tasks
        tasks = [ # (task, runs per iteration)
            (task_elapsed_time(), 1),
            (task_sensors(), 1),
            (task_memory_test(), 1),
        ]

        logger.info("Running")

        # main loop
        while True:
            now = time.time()

            # check runtime
            if now - start_time + last_run_time > MAX_RUN_TIME:
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

    # finished normally, remove elapsed time file
    try:
        os.remove(elapsed_path)
    except OSError as e:
        logger.warning('Cannot remove %s: %s', elapsed_path, str(e))

if __name__ == "__main__":
    main()
