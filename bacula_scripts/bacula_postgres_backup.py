#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Creates or deletes db dumps. Run before and after backups for a specific db.
E.g. /usr/local/bin/bacula-postgres-backup.py -c mf24
"""
import argparse
import datetime as dt
import glob
import os
import sys

from subprocess import Popen, PIPE
from helputils.core import mkdir_p, log

# Config
dbbackupdir = "/tmp/dbbackup"
mkdir_p(dbbackupdir)
os.environ["PGUSER"] = "postgres"


def createbackup(dbname, dbtype):
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
    p1 = Popen(cmd, stdout=f)
    o = p1.communicate()[0]
    log.debug(o)


def delbackup(dbname, dbtype):
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
    p = argparse.ArgumentParser()
    p.add_argument("-d", nargs=1)
    p.add_argument("-c", nargs=1)
    p.add_argument("-t", choices=["postgresql", "mongodb"], required=True)
    args = p.parse_args()
    if args.c:
        createbackup(args.c[0], args.t)
    if args.d:
        delbackup(args.d[0], args.t)
