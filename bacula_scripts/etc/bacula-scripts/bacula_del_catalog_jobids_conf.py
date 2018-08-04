""" bacula-del-catalog-jobids.py

WARNING: Use carefully!

Delete only the catalog entries, not the associated files, that are selected in configured SQL
query.

This script uses `echo delete jobid= | bconsole` to delete the selected jobids.

CONFIG: /etc/bacula-scripts/bacula_del_catalog_jobids_conf.py
"""

# Set dry_run to False to activate deletion. When set to True it's simulating deletion.
DRY_RUN = True
# Your custom SQL query, selecting the catalog entries to delete.
QUERY = """
SELECT jobid, name FROM job j
WHERE j.name LIKE 'c01%'
OR j.name LIKE '%-c01-%';
"""
