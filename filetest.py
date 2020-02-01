import ctypes as c
import ctypes.util

import os
import shutil
import hashlib

from logzero import logger

# constants
MAX_SIZE = 1024*1024*1024*2 # will allocate 2 GB at max on file system
RESERVE_SIZE = 1024*1024*100 # reserve at least 100 MB after allocation
FILE_NAME = "experiment_use_only_do_not_upload"
BLOCK_SIZE = 1024*1024

# prepare fallocate function
libc = c.CDLL(ctypes.util.find_library('c'))
libc.fallocate.restype = ctypes.c_int
libc.fallocate.argtypes = [c.c_int, c.c_int, c.c_int64, c.c_int64]

def fallocate(fd, mode, offset, length):
    # https://gist.github.com/NicolasT/1194957
    res = libc.fallocate(fd.fileno(), mode, offset, length)
    if res != 0:
        raise IOError(res, 'Failed to fallocate file')

class FileTest:
    def __init__(self, pwd):
        self.path = pwd + '/' + FILE_NAME
        self.fd = None

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
            try:
                with open(self.path, 'a') as fd:
                    fallocate(fd, 0, 0, self.size)
                self.fd = open(self.path, 'rb')
                self.update_hash()
            except:
                logger.error("Failed to allocate")
        return self

    def __exit__(self, *args):
        logger.info("Deleting experiment file")
        if self.fd: self.fd.close()
        self.fd = None
        try:
            os.remove(self.path)
        except OSError:
            pass

    def update_hash(self):
        md5 = hashlib.md5()
        self.fd.seek(0)
        while True:
            buf = self.fd.read(BLOCK_SIZE)
            if not data: break
            md5.update(data)
        self.hash = md5.hexdigest()

    def test(self):
        if not self.fd: return { 'file_size': 0,'file_changed': False}

        hash = self.hash
        update_hash()
        return {
            'file_size': self.size,
            'file_changed': hash != update_hash,
        }
