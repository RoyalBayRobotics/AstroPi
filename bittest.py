# Written by Rio Liu

# This file contains the experiment for testing memory bit flips
# At start, this will allocate a large chunk of memory and set half of them
# to 0, and the other half to 1
#
# When testing memory, the program simply create a checksum of current memory
# and compare it to the old checksum. If they don't match, that means the
# memory has been changed.
#
# Additionally, it will record which region the memory has changed, so we can
# potentially determine which value is more vulnerable to bit flipping

# For checksumming, I'm using zlib's adler32 function. From my testing, it
# performs faster than other hashing function in hashlib, and is able to detect
# a single bit change as well

import re
import numpy as np
from logzero import logger
from zlib import adler32

RESERVE_MEMORY_SIZE = 50 * 1024 * 1024 # reserve 50MB to system
FALLBACK_MEMORY_SIZE = 200 * 1024 * 1024 # if available memory cannot be determined, fall back to this

# this class allocates, checksums, and compare memory
# it uses python's generator syntax to achieve multitask without threading
class MemoryTest:
    def __init__(self, batch_size=-1):

        # this is the array that holds big memory
        self.array = None

        # Find out available memory size to use
        size = None
        regex = re.compile('^MemAvailable: +([0-9]+) kB$')
        try:
            with open('/proc/meminfo', 'r') as file:
                for line in file:
                    match = regex.match(line)
                    if match is not None:
                        size = int(match.group(1)) * 1024 - RESERVE_MEMORY_SIZE
                        break
        except OSError:
            pass

        if size is None:
            # failed to determine available memory, fall back to a predefined size
            logger.warning("Cannot find available memory")
            size = FALLBACK_MEMORY_SIZE
        elif size <= 0:
            # for some reason, there isn't enough memory left
            logger.error("Not enough memory for the experiment")
            return

        # batch size is used for spliting long-running checksum job into
        # smaller chunks so other tasks can execute in between
        self.batch_size = batch_size if batch_size >= 0 else size

        logger.info("Allocating %d bytes of memory", size)
        try:
            # Using both zeros and ones to see if different bits gives different results
            self.array = np.full(size, 0xFF, dtype=np.uint8)
            self.array[:self.array.size//2] = 0x00
            logger.info("Memory allocated")
        except (MemoryError, ValueError) as e:
            logger.error("Failed to allocate memory: %s", str(e))
            self.array = None

    # updates the memory checksum. yields the progress completed
    def update_hash(self):
        if self.array is None: return
        self.hash_zero = self.hash_one = 1

        # update checksum for the zero part of memory
        for i in range(0, self.array.size//2, self.batch_size):
            end = min(i+self.batch_size, self.array.size//2) # to prevent reading into one's region
            self.hash_zero = adler32(self.array.data[i:end], self.hash_zero)
            yield (i+self.batch_size) / self.array.size

        # update checksum for the one part of memory
        for i in range(self.array.size//2, self.array.size, self.batch_size):
            self.hash_one = adler32(self.array.data[i:i+self.batch_size], self.hash_one)
            yield (i+self.batch_size) / self.array.size

    # updates the memory checksum and compare it to the previous one
    # when running, it yields the progress completed
    # when finished, it yields a dict that contains the test result
    def test(self):
        if self.array is None: return
        hash_zero, hash_one = self.hash_zero, self.hash_one

        for prog in self.update_hash():
            # wait for it
            yield prog

        yield {
            'memory_zero_changed': hash_zero != self.hash_zero,
            'memory_one_changed': hash_one != self.hash_one,
        }
