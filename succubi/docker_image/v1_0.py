import json
import os
import tarfile
from collections import defaultdict
from shutil import (
    copytree,
    rmtree,
)


class _LayerNode(object):

    def __init__(self, id_=None, parent=None, child=None):
        self.id_ = id_
        self.parent = parent
        self.child = child


class Spec(object):

    # https://github.com/moby/moby/blob/master/image/spec/v1.md

    LAYER_TAR = 'layer.tar'
    REPOSITORIES = 'repositories'

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

    @classmethod
    def match(cls, handle):
        image_x_dir = handle['image_x_dir']
        repo_path = os.path.join(image_x_dir, cls.REPOSITORIES)
        return os.path.isfile(repo_path)

    @classmethod
    def __get_ordered_layer_ids(cls, image_x_dir):
        root_id = None
        nodes = defaultdict(_LayerNode)

        for item in os.listdir(image_x_dir):
            layer_dir = os.path.join(image_x_dir, item)
            if not os.path.isdir(layer_dir):
                continue

            nodes[item].id_ = item

            json_path = os.path.join(layer_dir, 'json')
            with open(json_path, 'r') as fd:
                json_data = json.load(fd)
            if json_data.get('id') != item:
                raise ValueError('Invalid layer dir: %s' % item)

            parent_id = json_data.get('parent', None)
            if parent_id is None:
                root_id = item
            else:
                nodes[parent_id].child = nodes[item]
                nodes[item].parent = nodes[parent_id]

        if root_id is None:
            raise ValueError('Can not find the root layer.')

        ordered_ids = []
        layer = nodes[root_id]
        while layer is not None:
            ordered_ids.append(layer.id_)
            layer = layer.child

        if len(ordered_ids) != len(nodes.keys()):
            raise ValueError('Some expected layer does not exist in these directories.')
        return ordered_ids

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
        ordered_layer_ids = cls.__get_ordered_layer_ids(image_x_dir)
        cls._register_layers(image_x_dir, target_layers_dir, ordered_layer_ids)
        yield repo_info, ordered_layer_ids

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
