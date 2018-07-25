#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula_db_backup.py

You can create or delete database dumps of postgresql, mongodb and mysql backends.

Use this for example within your job:
  Run Before Job = "bacula_db_backup -c mf24 -p '/db_dumps' -t postgresql"
  Run After Job = "bacula_db_backup -d mf24 -p '/db_dumps' -t postgresql"

To prevent permission issues, create a '/db_dumps' directory with 777 permissions:
`mkdir -m 777 /db_dump`. The directory has to be accessed namely by both postgres and bareos.

NO CONFIG NEEDED
"""
import argparse
import datetime as dt
import glob
import os
import sys

from subprocess import Popen, PIPE
from helputils.core import mkdir_p
from helputils.defaultlog import log

os.environ["PGUSER"] = "postgres"


def createbackup(dbname, dbtype, dbbackupdir=dbbackupdir):
    """Creates backup"""
    fn = "%s_%s_%s.db" % (dbtype, dbname, dt.datetime.now().strftime("%d.%m.%y"))
    log.debug(fn)
    fn = os.path.join(dbbackupdir, fn)
    f = open(fn, "w")
    if dbtype == "postgresql":
        cmd = ["pg_dump", dbname]
    elif dbtype == "mongodb":
        # By default mongodump dumps all db, but here we backup only the given dbname
        cmd = ["mongodump", "-d", dbname]
    elif dbtype == "mysql":
        # root can login by default to mysql
        cmd = ["mysqldump", dbname]
    p1 = Popen(cmd, stdout=f)
    o = p1.communicate()[0]
    log.debug(o)


def delbackup(dbname, dbtype, dbbackupdir=dbbackupdir):
    """Delete backups"""
    fn = os.path.join(dbbackupdir, "%s_%s" % (dbtype, dbname))
    bd = glob.glob("%s_*" % fn)
    log.debug(bd)
    if bd:
        os.remove(bd[0])


# Checking if services are up
services = ['bareos-dir', 'postgresql']
for x in services:
    p = Popen(['systemctl', 'is-active', x], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    out = out.decode("utf-8").strip()
    if "failed" == out:
        print("Exiting, because dependent services are down.")
        sys.exit()

# Argparse
def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-d", nargs=1, help="Delete a db dump backup.")
    p.add_argument("-c", nargs=1, help="Create a db dump backup.")
    p.add_argument(
        "-dir",
        nargs=1,
        help="Specify the db backup directory. E.g. '/tmp/dbbackup' ",
        required=True
    )
    p.add_argument("-t", choices=["postgresql", "mongodb", "mysql"], help="Choose the db type", required=True)
    args = p.parse_args()
    dbbackupdir = args.dir[0]
    mkdir_p(dbbackupdir)
    if args.c:
        createbackup(args.c[0], args.t, dbbackupdir=dbbackupdir)
    if args.d:
        delbackup(args.d[0], args.t, dbbackupdir=dbbackupdir)
