# bacula-encfs-backup.py
#
# Description:
# - Mounts encfs before backups and unmonts afterwards. If mount fails the job will be cancled.
# - In your bacula job add:
#   Run Before Job = /usr/local/bin/encfs-backup-bacula.py mount %i
#   Run After Job = /usr/local/bin/encfs-backup-bacula.py umount

# User notes:
# - Make sure encfs dir is owned by bacula (chown -R bacula:bacula /mnt/dropbox01/Dropbox/.encfs)
#   Also the dir where encfs is mounted to has to be owned by bacula
# - Create the dropbox dir for example in /mnt (not /root), because you need to have it in a traversable
#   dir (chmod +x dir).
# - Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before restoring.
# - If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it before
#   doing backups, because bareos can't stat dirs mounted by another user, so this script will cancel the
#   backup before it starts, when encfs is mounted by another user than bacula.

# Config:
encfs_passphrase = "abcdef"
encfs_dir = "/mnt/dropbox01/Dropbox/.your_encfs_dir"
mount_dir = "/mnt/decrypted_mounted_encfs_dir"
