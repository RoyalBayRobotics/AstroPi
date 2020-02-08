import re
import numpy as np
from logzero import logger
from zlib import adler32

RESERVE_MEMORY_SIZE = 50 * 1024 * 1024 # reserve 50MB to system
FALLBACK_MEMORY_SIZE = 500 * 1024 * 1024

# uses generator to implement multitask
class MemoryTest:
    def __init__(self, batch_size=-1):

        # Find out available memory size to use
        regex = re.compile('^MemAvailable: +([0-9]+) kB$')
        try:
            with open('/proc/meminfo', 'r') as file:
                for line in file:
                    match = regex.match(line)
                    if match is not None:
                        self.size = int(match.group(1)) * 1024 - RESERVE_MEMORY_SIZE
                        break
        except OSError:
            pass

        if self.size is None:
            logger.warning("Cannot find available memory")
            self.size = FALLBACK_MEMORY_SIZE
        elif self.size <= 0:
            logger.error("Not enough memory for the experiment")
            return

        self.batch_size = batch_size if batch_size != -1 else self.size

        logger.info("Allocating %d bytes of memory", self.size)
        try:
            # Using both zeros and ones to see if different bits gives different results
            self.array = np.full(self.size, 0xFF, dtype=np.uint8)
            self.array[:self.size//2] = 0x00
            logger.info("Memory allocated")
        except (MemoryError, ValueError) as e:
            logger.error("Failed to allocate memory: %s", str(e))
            self.array = None

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
