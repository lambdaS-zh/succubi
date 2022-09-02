import fcntl


class Lock(object):

    def __init__(self, id_):
        self._id = id_

    def acquire(self, excluding=False, blocking=True):
        pass

    def release(self):
        pass
