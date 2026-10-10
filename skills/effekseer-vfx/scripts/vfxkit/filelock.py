"""Exclusive, blocking, cross-process file locks on macOS, Linux and Windows. Standard library only.

POSIX uses flock(2); Windows locks the first byte of the file with msvcrt. Either way the kernel releases the lock when
the process exits, so a crashed run never leaves a lock behind and nothing is deleted to take one over.
"""
import os
import time

if os.name == 'nt':
    import msvcrt

    def acquire(stream):
        stream.seek(0)
        while True:
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                return
            except OSError:  # held by another process: wait like flock(LOCK_EX) does
                time.sleep(.05)

    def release(stream):
        stream.seek(0)
        msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def acquire(stream):
        fcntl.flock(stream, fcntl.LOCK_EX)

    def release(stream):
        fcntl.flock(stream, fcntl.LOCK_UN)
