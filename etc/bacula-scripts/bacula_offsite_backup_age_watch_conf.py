# bacula-offsite-backup-age-watch.py
#
# Description:
# Checking when last offsite backup was done for given jobnames and sending warning notification via mail if time exceeds given limit.
# Put this in cron.weekly

# Config:
max_offsite_age = 42  # max time in days before warning message for too old offsite backups
jobnames = ("example_jobname",)
