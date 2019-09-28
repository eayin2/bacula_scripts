""" bacula-del-media-orphans.py

Delete all catalog entries, which backup volume doesn't exist anymore.

CONFIG: /etc/bacula-scripts/bacula_del_media_orphans_conf.py
"""

# DRY_RUN: Set True to simulate deletion.
DRY_RUN = False
# LOG: Path of log file.
LOG = "/var/log/bareos/deleted_orphans.log"
# VERBOSE: True or False
VERBOSE = True
