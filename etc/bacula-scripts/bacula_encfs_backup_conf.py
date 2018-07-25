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
- Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before
restoring.
- If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it
before
  doing backups, because bareos can't stat dirs mounted by another user, so this script will
  cancel the backup before it starts, when encfs is mounted by another user than bacula.
- Optionally store the encfs private key outside your encfs directory at another location to
  increase security:
  1) First create an encfs6.xml by running the command normally in some directory. e.g.:
     encfs /tmp/encrypted /tmp/decrypted
  2) Copy /tmp/encrypted/.encfs6.xml (which contains the actual encryiption key within the
<encodedKeyData> directive)
     to some secure location. E.g. copy it to /root/.encfs-keys/
  3) Create the actual encfs directory with e.g.:
     ENCFS6_CONFIG="/root/.encfs-keys/encfs6_dropbox01.xml" encfs /mnt/dropbox01/Dropbox/.c01
/mnt/b01/
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

import os

ENCFS_PASSPHRASE = "abcdef"
ENCFS_DIR = "/mnt/dropbox01/Dropbox/.your_encfs_dir"
MOUNT_DIR = "/mnt/decrypted_mounted_encfs_dir"

# Optionally: Storing encfs6.xml outside the encfs dir for security reasons, else someone could simply
#  bruteforce our encfs
#  passphrase on dropbox. See:
#  Following suffices, no need to provide env parameter in Popen for the ENV variable
os.environ["ENCFS6_CONFIG"] = "/root/.encfs-keys/encfs6_dropbox01.xml"

# Don't change this unless you know what you are doing
cmd_mount = ["encfs", "--stdinpass", ENCFS_DIR, MOUNT_DIR]
cmd_password = ["echo", ENCFS_PASSPHRASE]
cmd_umount = ["fusermount", "-u", MOUNT_DIR]
cmd_lazy_umount = ["fusermount", "-z", "-u", MOUNT_DIR]
