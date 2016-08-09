#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-failed-jobs.py

Description:
Deletes volumes, which are associated with failed jobs.

Dev Notes:
Issuing delete twice, because running it just once, some entries persisted iirc (not sure).
(Would have to retest this and compare catalog entries between each deletion.)

Job Status Code meaning:
A Canceled by user
E Terminated in error
"""
import re
import os
import psycopg2
import sys
from subprocess import Popen, PIPE

from helputils.core import format_exception, systemd_services_up, log
sys.path.append("/etc/bacula-scripts")
from bacula_del_failed_jobs_conf import dry_run
from general_conf import db_host, db_user, db_name, services


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
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
