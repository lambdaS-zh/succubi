import json
import os
import tarfile
from collections import namedtuple
from shutil import (
    copytree,
    rmtree,
)


ImageItem = namedtuple('ImageItem', (
    'repo',
    'tag',
    'image_id',
    'ordered_layer_ids',
    'config',
))


class Spec(object):

    # https://github.com/moby/moby/blob/master/image/spec/v1.md

    LAYER_TAR = 'layer.tar'
    REPOSITORIES = 'repositories'
    JSON = 'json'

    @staticmethod
    def extract_stream(file_obj, image_x_dir):
        with tarfile.open(fileobj=file_obj) as tar_obj:
            tar_obj.extractall(path=image_x_dir)
        handle = {
            'image_x_dir':  image_x_dir,
        }
        return handle

    @staticmethod
    def extract_file(file_path, image_x_dir):
        with tarfile.open(name=file_path) as tar_obj:
            tar_obj.extractall(path=image_x_dir)
        handle = {
            'image_x_dir':  image_x_dir,
        }
        return handle

    @staticmethod
    def image_item(repo, tag, image_id, ordered_layer_ids, config):
        return ImageItem(
            repo=repo,
            tag=tag,
            image_id=image_id,
            ordered_layer_ids=ordered_layer_ids,
            config=config
        )

    @classmethod
    def match(cls, handle):
        image_x_dir = handle['image_x_dir']
        repo_path = os.path.join(image_x_dir, cls.REPOSITORIES)
        return os.path.isfile(repo_path)

    @classmethod
    def __get_ordered_layer_ids(cls, image_x_dir, top_layer_id):
        layer_id = top_layer_id
        top2bottom = []

        while layer_id is not None:
            layer_dir = os.path.join(image_x_dir, layer_id)
            if not os.path.isdir(layer_dir):
                raise ValueError('Layer %s is not found.' % layer_id)

            json_path = os.path.join(layer_dir, cls.JSON)
            try:
                with open(json_path, 'r') as fd:
                    json_data = json.load(fd)
            except (IOError, OSError, ValueError):
                raise ValueError('Invalid layer %s.' % layer_id)

            top2bottom.append(layer_id)
            layer_id = json_data.get('parent', None)

        return reversed(top2bottom)

    @classmethod
    def __load_repositories_info(cls, image_x_dir):
        repo_path = os.path.join(image_x_dir, cls.REPOSITORIES)
        if not os.path.isfile(repo_path):
            raise ValueError('Repositories file is not found in the image.')
        with open(repo_path, 'r') as fd:
            return json.load(fd)

    @classmethod
    def _register_layers(cls, image_x_dir, target_layers_dir, ordered_layer_ids):
        for layer_id in ordered_layer_ids:
            target_layer = os.path.join(target_layers_dir, layer_id)
            if os.path.isdir(target_layer):
                continue
            src_layer = os.path.join(image_x_dir, layer_id)
            copytree(src_layer, target_layer)

    @classmethod
    def load_spec_handle(cls, handle, target_layers_dir):
        image_x_dir = handle['image_x_dir']
        repo_info = cls.__load_repositories_info(image_x_dir)
        for repo, tags in repo_info.items():
            for tag, image_id in tags.items():
                # image_id =~ top_layer_id in spec v1.0
                ordered_layer_ids = cls.__get_ordered_layer_ids(image_x_dir, image_id)
                config_path = os.path.join(image_x_dir, image_id, cls.JSON)
                with open(config_path, 'r') as fd:
                    config_data = json.load(fd)
                cls._register_layers(image_x_dir, target_layers_dir, ordered_layer_ids)
                yield cls.image_item(repo, tag, image_id, ordered_layer_ids, config_data)

    @classmethod
    def _remove_f_node(cls, path):
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            rmtree(path)

    @classmethod
    def _remove_whiteout_files(cls, root_dir):
        prefix = '.wh.'
        prefix_len = len(prefix)
        for parent, dirs, files in os.walk(root_dir):
            for name in dirs + files:
                if not name.startswith(prefix):
                    continue
                target_name = name[prefix_len:]
                wh_path = os.path.join(parent, name)
                tg_path = os.path.join(parent, target_name)
                cls._remove_f_node(tg_path)
                cls._remove_f_node(wh_path)

    @classmethod
    def integrate_layers(cls, layers_dir, ordered_layer_ids, target_image_dir):
        for layer_id in ordered_layer_ids:
            layer_dir = os.path.join(layers_dir, layer_id)
            tar_path = os.path.join(layer_dir, cls.LAYER_TAR)
            with tarfile.open(name=tar_path) as tar_obj:
                tar_obj.extractall(path=target_image_dir)
            cls._remove_whiteout_files(target_image_dir)
