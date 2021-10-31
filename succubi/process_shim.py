import json
import os
import sys


def _use_dir(path):
    if os.path.isdir(path):
        return
    os.makedirs(path, 0o755)


def _set_env(environs):
    for name, value in environs.items():
        os.environ[name] = value


def _bind_mount(src, dst, rw):
    # TODO
    raise NotImplementedError()


def _umount(mount_point):
    # TODO
    raise NotImplementedError()


def _do_mount_maps(mount_maps):
    bound = []
    try:
        for item in mount_maps:
            src = item['Source']
            dst = item['Destination']
            rw = item['RW']
            _use_dir(dst)
            _bind_mount(src, dst, rw)
            bound.append(dst)
    except (OSError, IOError):
        for dst in reversed(bound):
            _umount(dst)
        raise


def _combine_cmd(entrypoint, cmd):
    return entrypoint + cmd


def _drop_euid():
    real_id = os.getuid()
    os.seteuid(real_id)
    os.setuid(real_id)


def shim(spec_path):
    # This is responsible for doing jobs which require
    # privileged permissions. After jobs finished, this
    # process should make itself un-privileged if its
    # real user is not root.
    with open(spec_path) as fd:
        spec = json.load(fd)
    os.remove(spec_path)

    _set_env(spec['environs'])
    _do_mount_maps(spec['bind_mounts'])
    _do_mount_maps(spec['volumes'])
    os.chroot(spec['root_dir'])

    _drop_euid()
    # TODO: check `detach` and run dumb-init


if __name__ == '__main__':
    shim(sys.argv[1])
