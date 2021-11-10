import json
import os
import pty
import sys
from subprocess import (
    call,
    check_call,
    CalledProcessError,
)

import daemon


STDIN_FILENO = 0
STDOUT_FILENO = 1
STDERR_FILENO = 2


def _use_node(src, dst):
    if os.path.isdir(src):
        if not os.path.isdir(dst):
            os.makedirs(dst, 0o755)
    elif os.path.isfile(src):
        if not os.path.isfile(dst):
            with open(dst, 'w'):
                pass
    else:
        raise OSError('Bad mount source: %s' % src)


def _set_env(environs):
    for name, value in environs.items():
        os.environ[name] = value


def _bind_mount(src, dst, rw):
    if rw:
        check_call(['mount', '--bind', '-o', 'bind', src, dst])
    else:
        check_call(['mount', '--bind', '-o', 'bind,ro', src, dst])


def _umount(mount_point):
    try:
        check_call(['umount', mount_point])
    except CalledProcessError:
        # ignore
        pass


def _do_mount_maps(mount_maps):
    bound = []
    try:
        for item in mount_maps:
            src = item['Source']
            dst = item['Destination']
            rw = item['RW']
            _use_node(src, dst)
            _bind_mount(src, dst, rw)
            bound.append(dst)
    except (OSError, IOError, CalledProcessError):
        for dst in reversed(bound):
            _umount(dst)
        raise


def _check_interactive(interactive):
    if not interactive:
        fd_null = os.open(os.devnull, os.O_RDONLY)
        os.dup2(fd_null, STDIN_FILENO)
        if fd_null > STDERR_FILENO:
            os.close(fd_null)


def _chroot(path):
    os.chdir(path)
    os.chroot(path)


def _change_working_dir(work_dir):
    if work_dir:
        os.chdir(work_dir)
    else:
        os.chdir('/')


def _drop_eid():
    real_uid = os.getuid()
    os.seteuid(real_uid)
    os.setuid(real_uid)

    real_gid = os.getgid()
    os.setegid(real_gid)
    os.setgid(real_gid)


def _spawn(spec):
    tty = spec['tty']
    cmd = spec['entrypoint'] + spec['cmd']

    if tty:
        return pty.spawn(cmd)

    return call(cmd)


def shim(spec_path):
    # This is responsible for doing jobs which require
    # privileged permissions. After jobs finished, this
    # process should make itself un-privileged if its
    # real user is not root.
    with open(spec_path) as fd:
        spec = json.load(fd)
    os.remove(spec_path)

    _do_mount_maps(spec['bind_mounts'])
    _do_mount_maps(spec['volumes'])
    _check_interactive(spec['interactive'])
    _chroot(spec['root_dir'])
    _drop_eid()

    _set_env(spec['environs'])

    # TODO: set signal handles to avoid zombies.

    if not spec['detach']:
        _change_working_dir(spec['working_dir'])
        return _spawn(spec)
    else:
        with daemon.DaemonContext():
            _change_working_dir(spec['working_dir'])
            return _spawn(spec)


if __name__ == '__main__':
    shim(sys.argv[1])
