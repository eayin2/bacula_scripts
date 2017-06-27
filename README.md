## bacula_scripts

#### Description
This package comes with various bacula scripts:

Meant for one time execution, when you want to delete something specifically:
- bacula_del_jobs
- bacula_del_catalog_jobids
- bacula_del_media_orphans (Removes catalog entries of inexistent volumes, you should run this better manually and not
  recurring in cron, because if you accidently remove a volume and want to migrate from an offsite backup, then the job
  entry would also be gone)

Helps you to find backups in a storage directory (e.g. if you don't have catalog entries for it anymore). It uses the
bacula tools bls to parse the metadata of the volumes in the given path.
- bacula_find_backups_bls

Meant for recurring execution (e.g. in cron.weekly) to clean the catalog for redundant entries or disk space for purged volumes.
- bacula_prune_all (Run this before bacula_del_purged_vols to force bacula to apply prunes rules for all volumes)
- bacula_del_purged_vols (will not delete a volume if there's an unpurged volume within the backup chain of it)
- bacula_del_failed_jobs (removes failed jobs in the catalog to keep it a little cleaner)

Offsite solution with udev and e.g. usb-sata disk (e.g. plugin once a week and store it at another room or place):
  Add udev rule to run bacula_offsite_udev.py on the system where you plug in your offsite disk (can be remote or also
  locally where the director is). See udev rule example in bacula_scripts/etc/udev/rules.d/
  - bacula_offsite_udev.py

  On director you run bacula_offsite_clean_and_umount with `Run after job` and bacula_offsite_backup_age_watch in e.g. cron.weekly
- bacula_offsite_backup_age_watch (warns you if your latest offsite backup is older than x days, as specified in its
  config. It looks in the catalog for the backups of the given jobname)
- bacula_offsite_clean_and_umount (Meant to run after an offsite job, to clean the offsite storage while its mounted of
  purged volumes)
- Example job resource. Notice that my sql query was test in postgresql, maybe ymmv. Also notice the
  line `AND to_timestamp(j1.jobtdate) > (current_timestamp - interval '180 days')` which will only grab the job entries
  that are younger than 180 days. The specified timespan should be the same as the pool's retention time. If it's not
  then bacula_del_purged_vols script may delete purged volumes and the offsite just copies already purged volumes back
  to here, providing the pool that you copy from uses a higher job retention than the copy job pool.:

```
Job {
  Name = c01full-lt-test01-phserver01
  Pool = Full-LT
  Client  = phserver01-fd
  Jobdefs = copy
  # This is the read storage, i.e. where to read the backups vols to copy from
  Storage = "sphserver01"
  Maximum Concurrent Jobs = 4
  Selection Type = "SQLQuery"
  Selection Pattern = "
    SELECT DISTINCT j1.jobid, j1.starttime
    FROM job j1, pool p1
    WHERE p1.name='Full-LT'
    AND p1.poolid=j1.poolid
    AND j1.type = 'B'
    AND j1.jobstatus IN ('T','W')
    AND j1.jobbytes > 0
    AND j1.name in ('lt-test01-phserver01')
    AND to_timestamp(j1.jobtdate) > (current_timestamp - interval '180 days')
    AND j1.jobid NOT IN (
      SELECT j2.priorjobid
      FROM job j2, pool p2
      WHERE p2.poolid = j2.poolid
      AND j2.type IN ('B','C')
      AND j2.jobstatus IN ('T','W')
      AND j2.priorjobid != 0
      AND p2.name='Full-LT-Copy01'
    )
    ORDER by j1.starttime;"
  Run After Job = "bacula_offsite_clean_and_umount.py phpc01e.your_remote_or_local_hostname."
}
```

#### Offsite solution with encfs and dropbox:
- bacula_encfs_backup.py (requires you to setup a dropbox and encfs dir within the dropbox on the system where the
  director is, then the script automatically mounts and umounts before and after backup).
- Example job resource:

```
Job {
    Name = lt-phpc01lin-c01-phpc01lin
    Run Before Job = "bacula_encfs_backup_bacula mount %i"
    Run After Job = "bacula_encfs_backup_bacula umount"
    Run After Failed Job = "bacula_encfs_backup_bacula umount"
    Client  = phpc01lin-fd
    FileSet = phpc01lin-c01
    Jobdefs = lt
    Storage = sdropbox01
    Maximum Concurrent Jobs = 1
  }
  Device {
    Name = ddropbox01
    Media Type = fdropbox01
    Archive Device = /mnt/b01
    LabelMedia = yes;
    Random Access = yes;
    AutomaticMount = yes;
    RemovableMedia = no;
    AlwaysOpen = no;
    Maximum Concurrent Jobs = 20;
  }
```

- Make sure encfs encrypted and mount dir is owned by bacula, so if your encfs dir with the dropbox mount is in
  "/mnt/dropbox01/Dropbox/.encfs", run
    `chown -R bacula:bacula /mnt/dropbox01/`
  And for the mount directory e.g.:
    `chown -R bacula:bacula /mnt/c01`
- Create the dropbox dir for example in /mnt (not /root), because you need to have it in a traversable
  dir (chmod +x dir).
- Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before restoring.
- If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it before
  doing backups, because bareos can't stat dirs mounted by another user, so this script will cancel the
  backup before it starts, when encfs is mounted by another user than bacula.
- It's recommended to store the encfs private key outside your encfs directory at another location to increase
  security.
  How to:
  1) First create an encfs6.xml by running the command normally in some directory. e.g.:
     encfs /tmp/encrypted /tmp/decrypted
  2) Copy /tmp/encrypted/.encfs6.xml (which contains the actual encryiption key within the <encodedKeyData> directive)
     to some secure location. E.g. copy it to /root/.encfs-keys/
  3) Create the actual encfs directory with e.g.:
     ENCFS6_CONFIG="/root/.encfs-keys/encfs6_dropbox01.xml" encfs /mnt/dropbox01/Dropbox/.c01 /mnt/b01/
  See this example config /etc/bacula-scripts/bacula_encfs_backups_conf.py:
```
     encfs_passphrase = "your_encfs_passphrase"
     encfs_dir = "/mnt/dropbox01/Dropbox/.c01"
     mount_dir = "/mnt/c01"
     # Here goes the .encfs6.xml file that we now store outside encfs
     os.environ["ENCFS6_CONFIG"] = "/root/.encfs-keys/encfs6_dropbox01.xml"
     cmd_mount = ["encfs", "--stdinpass", encfs_dir, mount_dir]
     cmd_password = ["echo", encfs_passphrase]
     cmd_umount = ["fusermount", "-u", mount_dir]
     cmd_lazy_umount = ["fusermount", "-z", "-u", mount_dir]
```

#### Configuration
See example config in etc/bacula_scripts and modify for your needs. general_conf.py is needed by multiple scripts.

#### Install
You can install this package with `pip3 install bacula_scripts`

#### Deps:
helputils, gymail, psycopg2

Also make sure bacula tools are installed, because the CLI tool `bls` is required.

#### Issues:
If bacula_offsite_udev doesn't work, try to initiate it manually in foreground with `bacula_offsite_udev add sdXY` (as
root), so that you can see the debug messages.

Also check in bconsole (on your bacula director) your offsite storage devices status. Moreover you can try to cancel all
copy backups and manually start each to see the bconsole messages for hints.

I run latter steps to find out that my offsite disk was full and thus backups failed.
