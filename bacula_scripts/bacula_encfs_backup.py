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
import os
import sys
import subprocess
from subprocess import PIPE

sys.path.append("/etc/bacula-scripts")
from bacula_encfs_backup_conf import encfs_passphrase, encfs_dir, mount_dir, cmd_mount, cmd_password, cmd_umount, cmd_lazy_umount

cmd_mount = ["encfs", "--stdinpass", encfs_dir, mount_dir]
cmd_password = ["echo", encfs_passphrase]
cmd_umount = ["fusermount", "-u", mount_dir]
cmd_lazy_umount = ["fusermount", "-z", "-u", mount_dir]


def umount(lazy=False):
    # Run After backup
    cmd = cmd_lazy_umount if lazy else cmd_umount
    p1 = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p1.communicate()
    print(out, err)
    print("Unmounted encfs")


def cancle_job(jobid):
    if jobid:
        print(jobid)
        p1 = subprocess.Popen(["echo", "cancel", "jobid=%s" % jobid, "yes"], stdout=PIPE, stderr=PIPE)
        p2 = subprocess.Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE, stderr=PIPE)
        p1.stdout.close()
        print(p2.communicate())


def mount(jobid=None):
    if os.path.ismount(mount_dir):
        print("Already mounted. Trying to unmount")
        umount()
        if os.path.ismount(mount_dir):
            print("Still mounted. Trying lazy unmount.")
            umount(lazy=True)
            if os.path.ismount(mount_dir):
                print("Couldn't be unmounted. Canceling job.")
                cancle_job(jobid)
                return
    else:
        p1 = subprocess.Popen(cmd_mount, stdin=PIPE)
        out, err = p1.communicate(input="{0}\n".format(encfs_passphrase).encode())
        if p1.returncode != 0:
            print("Rsync error: %s\n%s" % (out, err))
            cancle_job(jobid)
            return
        print(out, err)
        print("Mounted encfs")
    if not os.path.ismount(mount_dir):
        print("(E) encfs couldn't be mounted. Exiting %s" % err)
        cancle_job(jobid)
        sys.exit()


arg1 = sys.argv[1]
if arg1 == "mount":
    if len(sys.argv) == 3:
        jobid = sys.argv[2]
        mount(jobid)
    else:
        mount()
elif arg1 == "umount":
    umount()
