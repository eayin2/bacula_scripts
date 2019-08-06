#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-monitor.py
Check for each job whether there is a backup, that is older than a given time.
Send warning mails for old backups.

CONFIG: /etc/gymail.conf
CONFIG: /etc/bacula-scripts/bacula_monitor_conf.py
"""
import argparse
import datetime
import os
import re
import sys
import time
import traceback
from argparse import RawDescriptionHelpFormatter
from math import ceil
from subprocess import Popen, PIPE
from time import sleep

import pexpect
import psycopg2
from bacula_scripts.bacula_parser import bacula_parse
from gymail.core import send_mail
from helputils.core import format_exception, find_mountpoint, systemd_services_up
from helputils.defaultlog import log

sys.path.append("/etc/bacula-scripts")
import bacula_monitor_conf as conf_mod
from . import __version__
from general_conf import db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


class BaculaMonitor():

    def __init__(self, dry_run):
        self.dir_conf = bacula_parse("bareos-dir")
        self.dry_run = dry_run

    def run(self):
        job_conf = self.dir_conf.get('Job', None)
        job_excludes = CONF("job_excludes")
        if isinstance(job_excludes, str) or isinstance(job_excludes, int):
            print("Config error: job_excludes has to be a list.")
        if job_excludes:
            for job in job_excludes:
                job_conf.pop(job, None)
        jobs = list(job_conf)
        job_patterns = CONF("job_patterns")
        if isinstance(job_patterns, str) or isinstance(job_patterns, int):
            print("Config error: job_patterns has to be a list.")
        if job_patterns and jobs:
            job_patterns = "(" + ")|(".join(job_patterns) + ")"
            jobs = [job for job in jobs if not re.match(job_patterns, job)]
# j.jobid, j.name, m.volumename, s.name
        query = """
SELECT DISTINCT j.name, max(j.realendtime)
FROM job j, media m, jobmedia jm, storage s
WHERE m.mediaid=jm.mediaid
AND j.jobid=jm.jobid
AND s.storageid=m.storageid
AND j.name IN {0}
AND j.jobstatus IN ('T', 'W')
AND j.level IN ('F', 'I', 'D')
AND j.type IN ('B', 'C', 'c')
GROUP BY j.name;
""".format(tuple(jobs))
        try:
            con = psycopg2.connect(database=db_name, user=db_user, host=db_host,
                                   password=db_password)
            cur = con.cursor()
            cur.execute(query)
            res = cur.fetchall()
        except Exception as e:
            print(format_exception(e))
            return
        for job in res:
            name = job[0]
            realendtime = job[1]
            age = (datetime.datetime.now() - realendtime).days
            if age > CONF("max_days"):
                print(
                    "Warning: Backup job '{0}' is older than {2} days. Last backup is from "
                    "{1}.".format(name, realendtime, CONF("max_days"))
                )
                if not self.dry_run:
                    send_mail(
                        "Error",
                        "HIGH: Backup older than %s days" % CONF("max_days"),
                        "Backup job '{0}' is older than {2} days. Last backup is from "
                        "{1}. Check the backup-server for errors ASAP."
                        "".format(name, realendtime, CONF("max_days"))
                )
            else:
                print(
                    "OK: Backup job '{0}' is fine. Last backup is from "
                    "{1}.".format(name, realendtime)
                )

def run(dry_run=False):
    bacmon = BaculaMonitor(dry_run)
    bacmon.run()
    systemd_services_up(services)


def main():
    description = "%s\n\nVersion: bacula_scripts %s" % (__doc__, __version__)
    p = argparse.ArgumentParser(
        description=description,
        formatter_class=RawDescriptionHelpFormatter
    )
    p.add_argument("-r", action="store_true", help="Check if backup jobs have run lately, else" \
                   "sent warning mail.")
    p.add_argument("-dry", action="store_true", help="Run without sending a mail")
    args = p.parse_args()
    if args.r and args.dry:
        run(dry_run=True)
    elif args.r and not args.dry:
        run(dry_run=False)
