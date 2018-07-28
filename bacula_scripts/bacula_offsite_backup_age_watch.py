#!/usr/bin/python3
""" bacula-offsite-backup-age-watch.py

Check when the last offsite backup was performed and send a warning notification mail if the
backup is too old. Add a symlink to this script for example to cron.weekly.

CONFIG: /etc/bacula-scripts/bacula_offsite_backup_age_watch_conf.py
"""
import argparse
import os
import sys
import time
import traceback
from argparse import RawDescriptionHelpFormatter
from subprocess import Popen, PIPE

import psycopg2
from gymail.core import send_mail
from helputils.core import format_exception, systemd_services_up
sys.path.append("/etc/bacula-scripts")
import bacula_offsite_backup_age_watch_conf as conf_mod
from general_conf import db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


# Building our parameterized sql command
placeholder = "%s"
jobnames_placeholders = ', '.join([placeholder] * len(CONF('JOB_NAMES')))


def newest_offsite_backup():
    """Returns for newest offsite backup"""
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        query = "SELECT distinct j.jobtdate "\
                "FROM media m, job j, jobmedia jm "\
                "WHERE jm.mediaid=m.mediaid "\
                "AND jm.jobid=j.jobid "\
                "AND j.name IN (%s) " \
                "ORDER BY j.jobtdate DESC;" % jobnames_placeholders
        cur.execute(query % CONF('JOB_NAMES'))
        time = cur.fetchall()
        if not time:
            return None
        else:
            return int(time[0])
    except Exception as e:
        print(format_exception(e))
        return None


def run():
    systemd_services_up(services)
    offsite_ts = newest_offsite_backup()
    if offsite_ts:
        current_ts = int(time.time())
        offsite_days = (offsite_ts - current_ts) / (60*60*24)
        if offsite_days > CONF('MAX_OFFSITE_AGE_DAYS'):
            msg = "Offsite backups are too old %s" % (host, mp)
            send_mail(event="error", subject=os.path.basename(__file__), message=msg)
        else:
            print("Last copy job from %s is younger than %s days" % max_offsite_days)
    else:
        print("No copy backup found")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-c", action="store_true", help="Check backup age")
    args = p.parse_args()
    if args.c:
        run()
