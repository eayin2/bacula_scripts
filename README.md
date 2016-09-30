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

Offsite solution with encfs and dropbox:
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

#### Configuration
See example config in etc/bacula_scripts and modify for your needs. general_conf.py is needed by multiple scripts.

#### Install
You can install this package with `pip3 install bacula_scripts` (tested it in may 2016 successfully).

#### Deps: 
helputils, gymail, psycopg2


#### Issues:
If bacula_offsite_udev doesn't work, try to initiate it manually in foreground with `bacula_offsite_udev add sdXY` (as
root), so that you can see the debug messages.

Also check in bconsole (on your bacula director) your offsite storage devices status. Moreover you can try to cancel all
copy backups and manually start each to see the bconsole messages for hints.

I run latter steps to find out that my offsite disk was full and thus backups failed.
