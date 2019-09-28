#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula_db_backup.py

You can create or delete database dumps of postgresql, mongodb and mysql backends.

Use this for example within your job:
  Run Before Job = "bacula_db_backup -c mf24 -dir '/db_dumps' -t postgresql"
  Run After Job = "bacula_db_backup -d mf24 -dir '/db_dumps' -t postgresql"

To prevent permission issues, create a '/db_dumps' directory with 777 permissions:
`mkdir -m 777 /db_dump`. The directory has to be accessed namely by both postgres and bareos.

NO CONFIG NEEDED
"""
import argparse
import datetime as dt
import glob
import os
import re
import sys
from argparse import RawDescriptionHelpFormatter
from subprocess import Popen, PIPE

from helputils.core import mkdir_p
from helputils.defaultlog import log

os.environ["PGUSER"] = "postgres"


def createbackup(dbname, dbtype, pg_dump_custom_format=True, pg_dump_arg="", dbbackupdir="/tmp/dbbackupdir/"):
    """Creates backup"""
    if pg_dump_custom_format:
        pg_dump_arg += " -Fc"
    pg_dump_arg = pg_dump_arg.strip()
    fn = "%s_%s_%s.db" % (dbtype, dbname, dt.datetime.now().strftime("%d.%m.%y"))
    log.debug(fn)
    fn = os.path.join(dbbackupdir, fn)
    f = open(fn, "w")
    if dbtype == "postgresql":
        print("(RUN) pg_dump %s" % pg_dump_arg)
        cmd = ["pg_dump", pg_dump_arg, dbname]
    elif dbtype == "mongodb":
        # By default mongodump dumps all db, but here we backup only the given dbname
        cmd = ["mongodump", "-d", dbname]
    elif dbtype == "mysql":
        # root can login by default to mysql
        cmd = ["mysqldump", dbname]
    p1 = Popen(cmd, stdout=f)
    o = p1.communicate()[0]
    log.debug(o)


def delbackup(dbname, dbtype, dbbackupdir="/tmp/dbbackupdir"):
    """Delete backups"""
    fn = os.path.join(dbbackupdir, "%s_%s" % (dbtype, dbname))
    bd = glob.glob("%s_*" % fn)
    log.debug(bd)
    if bd:
        os.remove(bd[0])


def check_services():
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
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", nargs=1, help="Delete a db dump backup.")
    p.add_argument("-c", nargs=1, help="Create a db dump backup.")
    p.add_argument(
        "-dir",
        help="Specify the db backup directory. E.g. '/tmp/dbbackup' ",
        nargs=1,
        required=True
    )
    p.add_argument(
        "-pg_dump_arg",
        default="",
        help="Specify additional arg to pg_dump",
        nargs=1,
        required=False
    )
    p.add_argument(
        "-pg_dump_custom_format",
        action="store_true",
        default=True,
        help="Use pg_dump custom format -Fc. Custom format uses about level 6 compression",
        required=False
    )
    p.add_argument("-t", choices=["postgresql", "mongodb", "mysql"], help="Choose the db type", required=True)
    args = p.parse_args()
    dbbackupdir = args.dir[0]
    mkdir_p(dbbackupdir)
    if args.c:
        check_services()
        createbackup(
            args.c[0],
            args.t,
            pg_dump_custom_format=args.pg_dump_custom_format,
            pg_dump_arg=args.pg_dump_arg,
            dbbackupdir=dbbackupdir
        )
    if args.d:
        check_services()
        delbackup(args.d[0], args.t, dbbackupdir=dbbackupdir)
