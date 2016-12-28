#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-jobs.py
Description:
Removes full media vols which follow after each in a short timespan, to save space.
# F F F I F F F D F F F F F F F F
#   x       x       x x x x x   x
# So basically i want a full backup every 3 weeks, so i just get a list of all consecutive Full backups
# and i make sure to mark the Full backups that are allowed to be deleted, because only a Full backup which has a Full
# follower is allowed to be deleted:
# then i apply the even spread function and have maximum 1 Full backup within 3 weeks. even spread function should favor
# the older backups
"""
import re
import os
import sys
import traceback
import time
from datetime import datetime
from math import ceil
from subprocess import Popen, PIPE
from time import sleep

import pexpect
import psycopg2
from helputils.core import format_exception, find_mountpoint, log, systemd_services_up

sys.path.append("/etc/bacula-scripts")
from bacula_prune_scattered_conf import dry_run, fileset, poolnames, jname
from general_conf import db_host, db_user, db_name, services


def prune(b):
    """Deletes list of backups from disk and catalog"""
    for ts, nm in b:
        if not dry_run:
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
""".format(fileset, poolnames, jname).replace("\n", " ")


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


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
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
