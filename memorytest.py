import numpy as np
from zlib import adler32
from logzero import logger

SIZE = 1024*1024*300 # Will allocate 300 MB of ram

class MemoryTest:
    def __init__(self):
        logger.info("Allocating %d bytes of memory", SIZE)
        # Using both zeros and ones to see if different bits gives different results
        self.array = np.full(SIZE, 0xFF, dtype=np.uint8)
        self.array[:SIZE//2] = 0x00
        logger.info("Memory allocated")
        self._update_hash()

    def _update_hash(self):
        self.hash_zero = adler32(self.array.data[:SIZE//2])
        self.hash_one = adler32(self.array.data[SIZE//2:])

    def test(self):
        hash_zero, hash_one = self.hash_zero, self.hash_one
        self._update_hash()
        return {
            'memory_zero_changed': hash_zero != self.hash_zero,
            'memory_one_changed': hash_one != self.hash_one,
        }
