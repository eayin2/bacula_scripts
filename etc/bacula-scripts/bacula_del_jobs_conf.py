""" bacula-del-jobs.py

WARNING! Use with caution.

Delete all catalog entries that are associated to the given storage_name and their volume file
on the disk. Delete volumes that match the storage name or the job names.
Run this script only when you really want to delete something specifically.
This script doesn't work with remote storage devices.

If you need to remove backups from your dropbox encfs storage, then mount the encfs
storage. Use: `/usr/bin/bacula_encfs_backup mount`, which mounts it for example to /mnt/b01,
see /etc/bacula-scripts/bacula_encfs_backup_conf.py. bacula-del-jobs.py will then also remove
backups from /mnt/b01. Important! Unmount it afterwards, because the bacula user can't unmount
other users mountpoints.

If you use passphrases for your remote clients, run `ssh-add -t 10m /path/to/your/ssh/key`
before this script, else you'd get prompted repeatedly for the passphrase.

CONFIG: /etc/bacula_scripts/bacula_del_jobs_conf.py
"""

# DRY_RUN: True: Simulate deletion to test your filters. False: Run for real
DRY_RUN = True
# DEL_STORAGE_NAMES: Delete jobs and the associated on-disk volumes that match storage names
DEL_STORAGE_NAMES = ("s4tb02", "s1tb01", "s2tb01", "s3tb01", "sphserver01")
# DEL_STORAGE_NAMES_CATALOG: Delete jobs matching the storage name. Don't delete the volume file
DEL_STORAGE_NAMES_CATALOG = ("s3tb01",)
# DEL_JOB_NAMES: Delete jobs and associated volume files that match the job names.
#   Has to be a tuple, that is don't write like this ("lt-test01-phserver01").
DEL_JOB_NAMES = ("lt-test01-phserver01",)
# Filter for backups that are older a given starttime
DEL_OLDER = ("2016-12-24 23:59:59",)  # Use "YYYY-MM-DD HH:mm:ss" format
# Filter for backups that are newer a given starttime
DEL_NEWER = ("",)
# Choose between 'AND' or 'OR' operator, that is match all filters or one of them.
OPERATOR = "AND"
