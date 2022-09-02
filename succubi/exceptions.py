class ContainerAlreadyRunning(Exception):

    def __init__(self, id_or_name):
        super(ContainerAlreadyRunning, self).__init__(
            'Container %s is already running.' % id_or_name)
        self.id_or_name = id_or_name


class ImageAlreadyInUse(Exception):

    def __init__(self, id_or_name):
        super(ImageAlreadyInUse, self).__init__(
            'Image %s is already in use.' % id_or_name)
        self.id_or_name = id_or_name
