""" bacula_find_backups_bls.py

Find the on-disk volume inside a backup directory by parsing the volume information with `bls`
to match a client or fileset.

CONFIG: /etc/bacula-scripts/bacula_find_backups_bls_conf.py
"""

# FIND_BACKUP_DIR: Directory of the volumes to look into
FIND_BACKUP_DIR = "/mnt/12tb01/backups01"
# FIND_CLIENT: Client to look for inside the on-disk `bls`-parsed volume's metadata
FIND_CLIENT = "some_client-fd"
# FIND_FILESET: Fileset to look for, e.g. "Catalog"
FIND_FILESET = ""
