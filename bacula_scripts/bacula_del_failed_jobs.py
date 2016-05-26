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

from bacula_del_failed_jobs_conf import dry_run
from general_conf import db_host, db_user, db_name

# Checking if services are up
services = ['bareos-dir', 'postgresql']
for x in services:
    p = Popen(['systemctl', 'is-active', x], stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    out = out.decode("utf-8").strip()
    if "failed" == out:
        print("Exiting, because dependent services are down.")
        sys.exit()


def format_exception(e):
    """Usage: except Exception as e:
                  log.error(format_exception(e)) """
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1]))
    exception_str = 'Traceback (most recent call last):\n'
    exception_str += ''.join(exception_list)
    exception_str = exception_str[:-1]  # Removing the last \n
    return exception_str


try:
    con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
    cur = con.cursor()
    cur.execute("SELECT DISTINCT j.jobid, m.volumename FROM job j, jobmedia jm, media m WHERE j.JobStatus "
                "IN ('E', 'A', 'f') AND j.jobid=jm.jobid AND jm.mediaid=m.mediaid;")
    failed_job_jm_media = cur.fetchall()
except Exception as e:
    print(format_exception(e))
for jobid, volname in failed_job_jm_media:
    print("Deleting catalog entries for job (id: %s, volname: %s)." (jobid, volname))
    if not dry_run:
        p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
        p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()
        out, err = p2.communicate()
        print(out,err)
        p1 = Popen(["echo", "delete volume=%s yes" % tuple[0]], stdout=PIPE)
        p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
        p1.stdout.close()
        out, err = p2.communicate()
        print(out,err)
