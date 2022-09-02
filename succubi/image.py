import os
import tempfile
from six import string_types

from succubi.db import ImageDb
from succubi.docker_image.v1_0 import Spec as _Spec10
from succubi.docker_image.v1_x import Spec as _Spec1x


HOME = os.environ['HOME']
APP_ROOT = os.path.join(HOME, '.succubi')


def _use_dir(path):
    if os.path.isdir(path):
        return
    os.makedirs(path, 0o755)


def _dir_size(path):
    # TODO
    raise NotImplementedError()


class Image(object):

    LAYERS_ROOT = os.path.join(APP_ROOT, 'layers')
    IMAGES_ROOT = os.path.join(APP_ROOT, 'images')

    def __init__(self, image_id, repo, tag, size, timestamp):
        self._id = image_id
        self._repo = repo
        self._tag = tag
        self._size = size
        self._stamp = timestamp

    @property
    def id(self):
        return self._id

    def get_image_content_dir(self):
        return os.path.join(self.IMAGES_ROOT, self._id)

    def get_config(self):
        # TODO
        raise NotImplementedError()

    @classmethod
    def pull(cls, tag):
        raise NotImplementedError()

    @classmethod
    def load(cls, file_or_stream):
        with tempfile.TemporaryDirectory() as tmp_dir:
            if isinstance(file_or_stream, string_types):
                handle = _Spec10.extract_file(file_or_stream, tmp_dir)
            else:
                handle = _Spec10.extract_stream(file_or_stream, tmp_dir)

            if _Spec1x.match(handle):
                spec = _Spec1x
            elif _Spec10.match(handle):
                spec = _Spec10
            else:
                raise ValueError('Unsupported image.')

            _use_dir(cls.LAYERS_ROOT)
            _use_dir(cls.IMAGES_ROOT)

            image_items = spec.load_spec_handle(handle, cls.LAYERS_ROOT)
            for image_item in image_items:
                image_dir = os.path.join(cls.IMAGES_ROOT, image_item.image_id)
                _use_dir(image_dir)
                if not os.listdir(image_dir):
                    # empty dir means it's a new image
                    spec.integrate_layers(
                        cls.LAYERS_ROOT, image_item.ordered_layer_ids, image_dir)

                img_db = ImageDb()
                img_db.add(
                    image_id=image_item.image_id, repo=image_item.repo,
                    tag=image_item.tag, size=_dir_size(image_dir), config=image_item)

    @classmethod
    def list(cls, repo_tag=None):
        img_db = ImageDb()
        for image_id, repo, tag, size, stamp in img_db.list(repo_tag):
            yield cls(image_id, repo, tag, size, stamp)

    @classmethod
    def get(cls, id_or_repo_tag):
        img_db = ImageDb()
        raw = img_db.get_by_id(id_or_repo_tag)
        if raw is None:
            raw = img_db.get_by_repo_tag(id_or_repo_tag)

        if raw is None:
            return raw

        return cls(*raw)

    @classmethod
    def delete(cls, id_or_repo_tag):
        pass
