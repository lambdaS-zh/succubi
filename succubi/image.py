import os
import tempfile
from six import string_types

from succubi.docker_image.v1_0 import Spec as _Spec10
from succubi.docker_image.v1_x import Spec as _Spec1x


HOME = os.path.realpath('~')
APP_ROOT = os.path.join(HOME, '.succubi')


def _use_dir(path):
    if os.path.isdir(path):
        return
    os.makedirs(path, 0o755)


class Image(object):

    LAYERS_ROOT = os.path.join(APP_ROOT, 'layers')
    IMAGES_ROOT = os.path.join(APP_ROOT, 'images')

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
                # TODO: save image info into local db.

    @classmethod
    def list(cls, tag=None):
        raise NotImplementedError()

    @classmethod
    def get(cls, id_or_tag):
        raise NotImplementedError()
