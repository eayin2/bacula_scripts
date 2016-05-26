# bacula-del-catalog-jobids.py
#
# Description:
# Deletes only catalog entries (not files) with `echo delete jobid= | bconsole` for all jobifs
# that are selected in the sql query.

# Config:
dry_run = True
#dry_run = False

# Modify the query for your needs. In this example all jobs which name begins with c01 or which have the 
# string "-c01-" within their name will be selected and then deleted from the catalog.
query = "SELECT jobid, name FROM job j "\
        "WHERE j.name LIKE 'c01%' "\
        "OR j.name LIKE '%-c01-%';"
