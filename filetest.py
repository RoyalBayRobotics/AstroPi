import ctypes as c
import ctypes.util

import os
import shutil
from zlib import adler32

from logzero import logger

# constants
MAX_SIZE = 2147483647 # will allocate 2 GB at max on file system. it is also the max int32
RESERVE_SIZE = 1024*1024*100 # reserve at least 100 MB after allocation
FILE_NAME = "experiment_use_only_do_not_upload"
BLOCK_SIZE = 1024*1024

# prepare fallocate function
libc = c.CDLL(ctypes.util.find_library('c'), use_errno=True)
libc.fallocate.restype = ctypes.c_int
libc.fallocate.argtypes = [c.c_int, c.c_int, c.c_int32, c.c_int32]

def fallocate(fd, mode, offset, length):
    res = libc.fallocate(fd, mode, offset, length)
    if res != 0:
        raise IOError(c.get_errno(), 'Failed to fallocate file')

class FileTest:
    def __init__(self, pwd):
        self.path = pwd + '/' + FILE_NAME
        self.file = None

        # find out available storage space
        free = shutil.disk_usage(pwd).free - RESERVE_SIZE
        if free <= 0:
            logger.error("Not enough space for storage experiment")
            self.size = 0
        else:
            self.size = min(free, MAX_SIZE)

    def __enter__(self):
        if self.size > 0:
            logger.info("Allocating %d bytes on filesystem", self.size)
            fd = -1
            try:
                fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
                fallocate(fd, 0, 0, self.size)
                self.file = open(self.path, 'rb', 0)
                logger.info("File allocated")
                self.update_hash()
            except (IOError, OSError) as e:
                logger.error(str(e))
            finally:
                if fd != -1:
                    os.close(fd)
        return self

    def __exit__(self, *args):
        logger.info("Deleting experiment file")
        if self.file: self.file.close()
        self.file = None
        try:
            os.remove(self.path)
        except OSError:
            pass

    def update_hash(self):
        self.hash = 0xFFFFFF
        self.file.seek(0)
        while True:
            data = self.file.read(BLOCK_SIZE)
            if not data: break
            self.hash = adler32(data, self.hash)

    def test(self):
        if not self.file: return {'file_changed': False, 'file_size': 0}

        hash = self.hash
        update_hash()
        return {
            'file_changed': hash != update_hash,
            'file_size': self.size,
        }
