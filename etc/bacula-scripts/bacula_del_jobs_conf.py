# bacula-del-jobs.py
#
# Description:
# Deletes all catalog entries that are associated to the given storage_name and also tries to delete the volume on
# disk. Notice that it deletes volumes matching given storage name OR give job names.
# This is only intended to run when you really want to delete something specifically.

# Config:
dry_run = True
#dry_run = False
storagenames = ("s4tb02", "s1tb01", "s2tb01", "s3tb01", "sphserver01")
storagenames_del_only_catalog_entries = ("s3tb01")
jobnames = ("lt-test01-phserver01",)
# Choose either between jobname, storage, or_both (means all jobs matching either given storage or jobname) and and_both
# (means matching all job with the given storage name and jobname)
filters = "jobname" 
