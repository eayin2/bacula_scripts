""" bacula-offsite-backup-age-watch.py

Check when the last offsite backup was performed and send a warning notification mail if the
backup is too old. Add a symlink to this script for example to cron.weekly.

CONFIG: /etc/bacula-scripts/bacula_offsite_backup_age_watch_conf.py
"""

# Maximum backup age in days, before a warning mail is sent out
MAX_OFFSITE_AGE_DAYS = 42
JOB_NAMES = ("example_jobname",)
