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
- bacula_del_purged_vols (will not delete a volume if there's an unpurged volume within the backup chain of it)
- bacula_del_failed_jobs (removes failed jobs in the catalog to keep it a little cleaner)

- bacula_offsite_backup_age_watch (warns you if your latest offsite backup is older than x days, as specified in its
  config. It looks in the catalog for the backups of the given jobname)
- bacula_offsite_clean_and_umount (Meant to run after an offsite job, to clean the offsite storage while its mounted of
  purged volumes)


#### Configuration
See example config in etc/bacula_scripts and modify for your needs. general_conf.py is needed by multiple scripts.

#### Install
You can install this package with `pip3 install bacula_scripts` (tested it in may 2016 successfully).

#### Deps: 
helputils, gymail, psycopg2
