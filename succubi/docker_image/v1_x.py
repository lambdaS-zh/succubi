import json
import hashlib
import os
from collections import defaultdict
from succubi.docker_image.v1_0 import Spec as _Spec10


class Spec(_Spec10):

    # https://github.com/moby/moby/blob/master/image/spec/v1.1.md

    MANIFEST = 'manifest.json'

    @classmethod
    def match(cls, handle):
        image_x_dir = handle['image_x_dir']
        mani_path = os.path.join(image_x_dir, cls.MANIFEST)
        return os.path.isfile(mani_path)

    @classmethod
    def _load_manifest_item(cls, image_x_dir, target_layers_dir, item, layer2diff_ids):
        # Calculate the real diff_ids and make the map relationship.
        layer_ids = item['Layers']
        for layer_id in layer_ids:
            if layer2diff_ids.get(layer_id):
                continue

            layer_dir = os.path.join(image_x_dir, layer_id)
            tar_path = os.path.join(layer_dir, cls.LAYER_TAR)
            with open(tar_path, 'rb') as fd:
                h_ = hashlib.sha256(fd.read())
                diff_id = h_.hexdigest().lower()
                layer2diff_ids[layer_id] = diff_id

        diff2layer_ids = {v_: k_ for k_, v_ in layer2diff_ids.items()}

        config_name = item['Config']
        config_path = os.path.join(image_x_dir, config_name)
        with open(config_path, 'r') as fd:
            config_data = json.load(fd)
        with open(config_path, 'rb') as fd:
            h_ = hashlib.sha256(fd.read())
            image_id = h_.hexdigest().lower()

        ordered_diff_ids = config_data['rootfs']['diff_ids']
        ordered_layer_ids = [diff2layer_ids[d_] for d_ in ordered_diff_ids]
        cls._register_layers(image_x_dir, target_layers_dir, ordered_layer_ids)

        repo_info = defaultdict(dict)
        for tag_item in item['RepoTags']:
            colon_n = tag_item.index(':')  # SHALL NOT use split
            repo = tag_item[:colon_n]
            tag = tag_item[colon_n + 1:]
            repo_info[repo][tag] = image_id

        return repo_info, ordered_layer_ids

    @classmethod
    def load_spec_handle(cls, handle, target_layers_dir):
        image_x_dir = handle['image_x_dir']

        mani_path = os.path.join(image_x_dir, cls.MANIFEST)
        with open(mani_path, 'r') as fd:
            mani_data = json.load(fd)

        layer2diff_ids = {}  # cache
        for item in mani_data:
            yield cls._load_manifest_item(
                image_x_dir, target_layers_dir, item, layer2diff_ids)
