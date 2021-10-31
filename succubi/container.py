import json
import os
import sys
from shutil import (
    copytree,
    rmtree,
)
from subprocess import check_call
from tempfile import gettempdir
from uuid import uuid4


HOME = os.environ['HOME']
APP_ROOT = os.path.join(HOME, '.succubi')


def _use_dir(path):
    if os.path.isdir(path):
        return
    os.makedirs(path, 0o755)


def _gen_con_id():
    return uuid4().hex


class Container(object):

    CONTAINERS_ROOT = os.path.join(APP_ROOT, 'containers')

    def __init__(self, container_id, container_name, image,
                 detach=False, interactive=False, tty=False,
                 environs=(), bind_mounts=(), volumes=(),
                 entrypoint=(), cmd=()):
        self._id = container_id
        self._name = container_name
        self._image = image
        self._detach = detach
        self._interactive = interactive
        self._tty = tty
        self._environs = environs
        self._bind_mounts = bind_mounts
        self._volumes = volumes
        self._entrypoint = entrypoint
        self._cmd = cmd

    @property
    def root_dir(self):
        return os.path.join(self.CONTAINERS_ROOT, self._id)

    @classmethod
    def create(cls, **kwargs):
        new_con_id = _gen_con_id()
        container_dir = os.path.join(cls.CONTAINERS_ROOT, new_con_id)
        _use_dir(container_dir)
        try:
            image = kwargs['image']
            image_dir = image.get_image_content_dir()
            copytree(image_dir, container_dir)
            # TODO: save db info and json info
            return cls(new_con_id, **kwargs)
        except (OSError, IOError):
            rmtree(container_dir, ignore_errors=True)
            raise

    @classmethod
    def run(cls, **kwargs):
        container = cls.create(**kwargs)
        return container.start()

    @classmethod
    def delete(cls):
        pass

    def start(self):
        # TODO: check if it is already running and set user lock.
        # TODO: check if name is in use.
        spec = {
            'root_dir':     self.root_dir,
            'id':           self._id,
            'name':         self._name,
            'image':        self._image.id,
            'detach':       self._detach,
            'interactive':  self._interactive,
            'tty':          self._tty,
            'environs':     self._environs,
            'bind_mounts':  self._bind_mounts,
            'volumes':      self._volumes,
            'entrypoint':   self._entrypoint,
            'cmd':          self._cmd,
        }

        file_path = os.path.join(gettempdir(), '.succubi.%s.shim_spec' % self._id)
        content = json.dumps(spec)

        with open(file_path, 'w') as fd:
            fd.write(content)

        check_call([sys.argv[0], '-m', 'succubi.process_shim', file_path])

    def stop(self):
        pass
