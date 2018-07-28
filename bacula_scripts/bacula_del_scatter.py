#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-jobs.py

Delete redundant full media vols which are following to narrowly.

Example:
 F F F I F F F D F F F F F F F F
   x       x       x x x x x   x

We want a full backup every 3 weeks, so we get a list of all consecutive Full backups
and make sure to mark the Full backups, that are allowed to be deleted. Only Full backups,
which have a Full following backup are allowed to be deleted.
Then apply the even spread function and have at maximum 1 Full backup within 3 weeks.
The even spread function favors older backups.

CONFIG: /etc/bacula-scripts/bacula_prune_scattered_conf.py
"""
import argparse
import os
import re
import sys
import time
import traceback
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from math import ceil
from subprocess import Popen, PIPE
from time import sleep

import pexpect
import psycopg2
from helputils.core import format_exception, find_mountpoint, systemd_services_up
from helputils.defaultlog import log

sys.path.append("/etc/bacula-scripts")
import bacula_prune_scattered_conf as conf_mod
from general_conf import db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


def prune(b):
    """Deletes list of backups from disk and catalog"""
    for ts, nm in b:
        if not CONF('DRY_RUN'):
            p1 = pexpect.spawn("/usr/sbin/bconsole")
            p1.logfile = open("/tmp/pexpectlog", "wb")
            p1.sendline('prune volume=%s' % nm)
            p1.expect("mod\/no\)\:")
            p1.sendline("mod")
            p1.expect(["new", "retention", "period", "Volume"])
            p1.sendline("1")
            p1.expect("current")
            p1.sendline("yes")
        log.debug("Pruned %s" % nm)


query = """
SELECT DISTINCT j.jobtdate, m.volumename
FROM media m, job j, jobmedia jm, fileset f, pool p
WHERE m.mediaid=jm.mediaid
AND f.filesetid=j.filesetid
AND f.fileset='{0}'
AND p.poolid=m.poolid
AND p.name IN ({1})
AND j.level='F'
AND j.type!='c'
AND j.type!='C'
AND j.type!='R'
AND j.jobid=jm.jobid
AND m.volstatus!='Purged'
AND j.name LIKE '{2}'
ORDER BY j.jobtdate;
""".format(CONF('FILESET'), CONF('POOL_NAMES'), CONF('JOB_NAME')).replace("\n", " ")


def backuplevel(x):
    """Returns backup level by looking for the words full, incremental and differential in the string"""
    x = x.lower()
    if "full" in x:
        return "f"
    elif "diff" in x:
        return "d"
    elif "inc" in x:
        return "i"
    else:
        return None


def evenspread(sequence, num):
    length = float(len(sequence))
    for i in range(num):
        yield sequence[int(ceil(i * length / num))]


def run(dry_run=False):
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        print(query)
        cur.execute(query)
        res = cur.fetchall()
    except Exception as e:
        print(format_exception(e))
        return
    cull = list()
    for i, x in enumerate(res):
        ts = x[0]
        na = x[1]
        # and (ts - prevts) < 8*24*60*60:
        if i != 0 and prevlevel == backuplevel(na):
            cull.append(prevx)
        prevlevel = backuplevel(na)
        prevts = ts
        prevna = na
        prevx = x
    # get first and last and see what timespan
    ts1 = cull[0][0]
    ts2 = cull[-1][0]
    timespan = (ts2 - ts1)/60/60/24
    num = ceil(timespan/24)  # rounds up. dividing by 24 for full backup every 24 days
    print(num)
    keep = [x for x in evenspread(cull, num)]
    prunes = [x for x in cull if x[1] not in [y[1] for y in keep]]
    print("in total %s" % len(res))
    print("keeping %s" % len(keep))
    print("purging %s" % len(prunes))
    prune(prunes)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete redundant full media volumes")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    elif args.d and not args.dry:
        run(dry_run=False)
