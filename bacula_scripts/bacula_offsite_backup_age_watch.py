#!/usr/bin/python3
""" bacula-offsite-backup-age-watch.py
Description:
Checking when last offsite backup was done and sending warning notification via mail if time exceeds given limit.
Put this in cron.weekly
"""
import sys
import os
import time
import traceback
from subprocess import Popen, PIPE

import psycopg2

from gymail.core import send_mail
from helputils.core import format_exception, systemd_services_up
sys.path.append("/etc/bacula-scripts")
from bacula_offsite_backup_age_watch_conf import max_offsite_age, jobnames
from general_conf import db_host, db_user, db_name, services

# Building our parameterized sql command
placeholder = "%s"
jobnames_placeholders = ', '.join([placeholder] * len(jobnames))


def newest_offsite_backup():
    """Returns for newest offsite backup"""
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
        cur = con.cursor()
        query = "SELECT distinct j.jobtdate "\
                "FROM media m, job j, jobmedia jm "\
                "WHERE jm.mediaid=m.mediaid "\
                "AND jm.jobid=j.jobid "\
                "AND j.name IN (%s) " \
                "ORDER BY j.jobtdate DESC;" % jobnames_placeholders
        cur.execute(query % jobnames)
        time = cur.fetchall()
        if not time:
            return None
        else:
            return int(time[0])
    except Exception as e:
        print(format_exception(e))
        return None


def main():
    systemd_services_up(services)
    offsite_ts = newest_offsite_backup()
    if offsite_ts:
        current_ts = int(time.time())
        offsite_days = (offsite_ts - current_ts) / (60*60*24)
        if offsite_days > max_offsite_days:
            msg = "Offsite backups are too old %s" % (host, mp)
            send_mail(event="error", subject=os.path.basename(__file__), message=msg)
        else:
            print("Last copy job from %s is younger than %s days" % max_offsite_days)
    else:
        print("No copy backup found")
