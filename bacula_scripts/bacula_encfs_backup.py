#!/usr/bin/python3
""" bacula-encfs-backup.py

Mount encfs before backups and unmonts afterwards. If mount fails the job will be cancled.

In your bacula job add:
  Run Before Job = /usr/local/bin/encfs-backup-bacula.py mount %i
  Run After Job = /usr/local/bin/encfs-backup-bacula.py umount

User notes:
- Make sure encfs encrypted and mount dir is owned by bacula. If your encfs dir with the dropbox
  mount is in "/mnt/dropbox01/Dropbox/.encfs", do:
   `chown -R bacula:bacula /mnt/dropbox01/`
  And for the mount directory e.g.:
   `chown -R bacula:bacula /mnt/c01`
- Create the dropbox dir for example inside /mnt (not /root), because you need to have it in a
  traversable.
  `dir (chmod +x dir)`
- Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before restoring.
- If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it before
  doing backups, because bareos can't stat dirs mounted by another user, so this script will
  cancel the backup before it starts, when encfs is mounted by another user than bacula.
- Optionally store the encfs private key outside your encfs directory at another location to
  increase security:
  1) First create an encfs6.xml by running the command normally in some directory. e.g.:
     encfs /tmp/encrypted /tmp/decrypted
  2) Copy /tmp/encrypted/.encfs6.xml (which contains the actual encryiption key within the <encodedKeyData> directive)
     to some secure location. E.g. copy it to /root/.encfs-keys/
  3) Create the actual encfs directory with e.g.:
     ENCFS6_CONFIG="/root/.encfs-keys/encfs6_dropbox01.xml" encfs /mnt/dropbox01/Dropbox/.c01 /mnt/b01/
  See this example config /etc/bacula-scripts/bacula_encfs_backups_conf.py:
    encfs_passphrase = "your_encfs_passphrase"
    encfs_dir = "/mnt/dropbox01/Dropbox/.c01"
    mount_dir = "/mnt/c01"
    # Here goes the .encfs6.xml file that we now store outside encfs
    os.environ["ENCFS6_CONFIG"] = "/root/.encfs-keys/encfs6_dropbox01.xml"
    cmd_mount = ["encfs", "--stdinpass", encfs_dir, mount_dir]
    cmd_password = ["echo", encfs_passphrase]
    cmd_umount = ["fusermount", "-u", mount_dir]
    cmd_lazy_umount = ["fusermount", "-z", "-u", mount_dir]

CONFIG: /etc/bacula-scripts/bacula_encfs_backup_conf.py
"""
import grp
import os
import pwd
import sys
import subprocess
from subprocess import PIPE

from helputils.core import umount
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
import bacula_encfs_backup_conf as conf_mod


def CONF(attr):
    return getattr(conf_mod, attr, None)


def cancle_job(jobid):
    if jobid:
        log.debug(jobid)
        p1 = subprocess.Popen(["echo", "cancel", "jobid=%s" % jobid, "yes"], stdout=PIPE, stderr=PIPE)
        p2 = subprocess.Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        p1.stdout.close()
        log.debug(p2.communicate())


def encfs_mount(jobid=None):
    if os.path.ismount(CONF('MOUNT_DIR')):
        log.info("Already mounted. Trying to unmount")
        umount(CONF('MOUNT_DIR'), fuser=True)
        if os.path.ismount(CONF('MOUNT_DIR')):
            log.warning("Still mounted. Trying lazy unmount.")
            umount(CONF('MOUNT_DIR'), lazy=True, fuser=True)
            if os.path.ismount(CONF('MOUNT_DIR')):
                log.error("Couldn't be unmounted. Canceling job.")
                cancle_job(jobid)
                sys.exit()
    p1 = subprocess.Popen(CONF('cmd_mount'), stdin=PIPE)
    out, err = p1.communicate(input="{0}\n".format(CONF('ENCFS_PASSPHRASE')).encode())
    if p1.returncode != 0:
        log.error("failed: out: %s err: %s" % (out, err))
        cancle_job(jobid)
        return
    log.debug("out: %s, err %s" % (out, err))
    log.info("Mounted encfs")
    if not os.path.ismount(CONF('MOUNT_DIR')):
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
        umount(CONF('MOUNT_DIR'), fuser=True)
