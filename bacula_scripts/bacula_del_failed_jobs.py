#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-failed-jobs.py

Delete all volumes that are associated to failed jobs, to be the catalog cleaner.

Developing notes:
Issuing delete twice, because running it just once some entries persisted.
Eventually redo tests by comparing catalog entries between each deletion.

Job Status Code meanings:
A Canceled by user
E Terminated in error

NO CONFIG NEEDED
"""
import argparse
import os
import psycopg2
import re
import sys
from subprocess import Popen, PIPE

from helputils.core import format_exception, systemd_services_up
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
from general_conf import db_host, db_user, db_name, db_password, services


def run(dry_run=True):
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute("SELECT DISTINCT j.jobid, m.volumename FROM job j, jobmedia jm, media m WHERE j.JobStatus "
                    "IN ('E', 'A', 'f') AND j.jobid=jm.jobid AND jm.mediaid=m.mediaid;")
        failed_job_jm_media = cur.fetchall()
    except Exception as e:
        log.error(format_exception(e))
    for jobid, volname in failed_job_jm_media:
        log.info("Deleting catalog entries for job (id: %s, volname: %s)." % (jobid, volname))
        if not dry_run:
            p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
            p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            p1 = Popen(["echo", "delete volume=%s yes" % jobid], stdout=PIPE)
            p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            log.debug("out: %s, err: %s" % (out, err))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-d", action="store_true", help="Delete all failed jobs associated volumes")
    p.add_argument("-dry", action="store_true", help="Dry run, simulates deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    if args.d and not args.dry:
        run(dry_run=False)
