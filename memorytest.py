import numpy as np
import hashlib

SIZE = 1024*1024*300 # Will allocate 300 MB of ram

class MemoryTest:
    def __init__(self):
        # Using both zeros and ones to see if different bits gives different results
        self.array = np.full(SIZE, 0xFF, dtype=np.uint8)
        self.array[:SIZE//2] = 0x00
        self._update_hash()

    def _update_hash(self):
        self.hash_zero = hashlib.md5(self.array.data[:SIZE//2]).hexdigest()
        self.hash_one = hashlib.md5(self.array.data[SIZE//2:]).hexdigest()

    def test(self):
        hash_zero, hash_one = self.hash_zero, self.hash_one
        self._update_hash()
        return {
            'memory_zero_changed': hash_zero != self.hash_zero,
            'memory_one_changed': hash_one != self.hash_one,
        }
