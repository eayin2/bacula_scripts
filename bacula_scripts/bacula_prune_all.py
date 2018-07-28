#!/usr/bin/python3
# -*- coding: utf-8-*-
""" bacula-prune-all.py

Prune all existing volumes. Run `bconsole prune volume=x yes` for all existing volumes. Latter
command will only prune the volume, if the configured retention time is passed.

Run this before bacula_del_purged_vols to force bacula to apply prunes rules for all volumes.

NO CONFIG
"""
import argparse
import os
import psycopg2
import re
import sys
from argparse import RawDescriptionHelpFormatter
from subprocess import Popen, PIPE

from helputils.core import format_exception, systemd_services_up
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
from general_conf import db_host, db_user, db_name, db_password, services

sql = """
SELECT DISTINCT m.volumename FROM jobmedia jm, media m, job j
WHERE m.mediaid=jm.mediaid
AND j.jobid=jm.jobid
AND m.volstatus='Used'
AND j.jobbytes!=0
AND j.jobfiles!=0
AND j.jobstatus='T';
"""


def run(dry_run=False):
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute(sql)
        volnames = cur.fetchall()
    except Exception as e:
        log.error(format_exception(e))
    for vn in volnames:
        print("Pruning volname %s." % (vn))
        if not dry_run:
            p1 = Popen(["echo", "prune volume=%s yes" % vn], stdout=PIPE)
            p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            log.debug("out: %s, err: %s" % (out, err))

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-p", action="store_true", help="Prune all volumes")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.p and args.dry:
        run(dry_run=True)
    elif args.p and not args.dry:
        run(dry_run=False)
