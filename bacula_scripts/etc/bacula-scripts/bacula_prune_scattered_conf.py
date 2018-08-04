""" bacula-del-jobs.py

Delete redundant full media vols which are following to narrowly.

Example:
 F F F I F F F D F F F F F F F F
   x       x       x x x x x   x

We want a full backup every 3 weeks, so we get a list of all consecutive Full backups
and make sure to mark the Full backups, that are allowed to be deleted. Only Full backups,
which have a Full following backup are allowed to be deleted.
Then apply the even spread function and have at maximum 1 Full backup within 3 weeks.
The even spread function favors older backups.

CONFIG: /etc/bacula-scripts/bacula_prune_scattered_conf.py
"""

# Enter the fileset, pool names and job name which you want full backups scatter-deleted
FILESET = "rootfs"
POOL_NAMES = "'Full-ST', 'Differential-ST', 'Incremental-ST'"
JNAME = "st-rootfs-server01"
DRY_RUN = False
