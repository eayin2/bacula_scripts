#!/usr/bin/python3
""" bacula-encfs-backup.py

Description:
- Mounts encfs before backups and unmonts afterwards. If mount fails the job will be cancled.
- In your bacula job add:
  Run Before Job = /usr/local/bin/encfs-backup-bacula.py mount %i
  Run After Job = /usr/local/bin/encfs-backup-bacula.py umount

User notes:
- Make sure encfs dir is owned by bacula (chown -R bacula:bacula /mnt/dropbox01/Dropbox/.encfs)
  Also the dir where encfs is mounted to has to be owned by bacula
- Create the dropbox dir for example in /mnt (not /root), because you need to have it in a traversable
  dir (chmod +x dir).
- Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before restoring.
- If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it before
  doing backups, because bareos can't stat dirs mounted by another user, so this script will cancel the
  backup before it starts, when encfs is mounted by another user than bacula.
"""
import grp
import os
import pwd
import sys
import subprocess
from subprocess import PIPE

from helputils.core import umount, log
sys.path.append("/etc/bacula-scripts")
from bacula_encfs_backup_conf import encfs_passphrase, encfs_dir, mount_dir, cmd_mount, cmd_password

cmd_mount = ["encfs", "--stdinpass", encfs_dir, mount_dir]
cmd_password = ["echo", encfs_passphrase]


def cancle_job(jobid):
    if jobid:
        log.debug(jobid)
        p1 = subprocess.Popen(["echo", "cancel", "jobid=%s" % jobid, "yes"], stdout=PIPE, stderr=PIPE)
        p2 = subprocess.Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        p1.stdout.close()
        log.debug(p2.communicate())


def encfs_mount(jobid=None):
    if os.path.ismount(mount_dir):
        log.info("Already mounted. Trying to unmount")
        umount(mount_dir, fuser=True)
        if os.path.ismount(mount_dir):
            log.warning("Still mounted. Trying lazy unmount.")
            umount(mount_dir, lazy=True, fuser=True)
            if os.path.ismount(mount_dir):
                log.error("Couldn't be unmounted. Canceling job.")
                cancle_job(jobid)
                sys.exit()
    p1 = subprocess.Popen(cmd_mount, stdin=PIPE)
    out, err = p1.communicate(input="{0}\n".format(encfs_passphrase).encode())
    if p1.returncode != 0:
        log.error("failed: out: %s err: %s" % (out, err))
        cancle_job(jobid)
        return
    log.debug("out: %s, err %s" % (out, err))
    log.info("Mounted encfs")
    if not os.path.ismount(mount_dir):
        log.error("(E) encfs couldn't be mounted. Exiting %s")
        cancle_job(jobid)
        sys.exit()


def main():
    arg1 = sys.argv[1]
    if arg1 == "mount":
        if len(sys.argv) == 3:
            jobid = sys.argv[2]
            encfs_mount(jobid)
        else:
            encfs_mount()
    elif arg1 == "umount":
        umount(mount_dir, fuser=True)
