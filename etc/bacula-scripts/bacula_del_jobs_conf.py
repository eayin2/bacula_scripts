# bacula-del-jobs.py
#
# Description:
# Deletes all catalog entries that are associated to the given storage_name and also tries to delete the volume on
# disk. Notice that it deletes volumes matching given storage name OR give job names. Additionally you can also delete
# job newer or older to a give date. Use filters "newer_than_starttime" (deletes all backups newer than given backup
# starttime) or "older_than_starttime" (deletes all backups older than given starttime) respectively. Make sure to keep
# the parenthesis and comma for single tuples (see below example).
# This is only intended to run when you really want to delete something specifically.

# Config:
dry_run = True  # False|True
storagenames = ("s4tb02", "s1tb01", "s2tb01", "s3tb01", "sphserver01")
storagenames_del_only_catalog_entries = ("s3tb01")
jobnames = ("lt-test01-phserver01",)
# Available filters: 
#  jobname 
#  storage
#  or_both (all jobs matching either given storage or jobname), 
#  and_both (all job with the given storage name and jobname)
#  starttime
starttime = ("2016-12-24 23:59:59",)  # Use "YYYY-MM-DD HH:mm:ss" format
filters = "newer_than_starttime" 
