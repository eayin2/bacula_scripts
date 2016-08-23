#!/usr/bin/python3
# -*- coding: utf-8-*-
""" bacula-prune-all.py                                                                                                                                                                  
Runs `bconsole prune volume=x yes` for all existing volumes. Latter command will only prune the volume if the configured
retention time is passed.
"""
import re
import os
import psycopg2
import sys
from subprocess import Popen, PIPE

from helputils.core import format_exception, systemd_services_up, log
sys.path.append("/etc/bacula-scripts")
from general_conf import db_host, db_user, db_name, services

dry_run = False
sql = "SELECT DISTINCT m.volumename FROM jobmedia jm, media m, job j "\
      "WHERE m.mediaid=jm.mediaid "\
      "AND j.jobid=jm.jobid "\
      "AND m.volstatus='Used' "\
      "AND j.jobbytes!=0 "\
      "AND j.jobfiles!=0 "\
      "AND j.jobstatus='T';"


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
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
