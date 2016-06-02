#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-catalog-jobids.py
Description:
Deletes only catalog entries (not files) with `echo delete jobid= | bconsole` for all jobifs
that are selected in the sql query.
"""
import imp
import re
import os
import sys
import traceback
import time
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

from helputils.core import format_exception, log, systemd_services_up
sys.path.append("/etc/bacula-scripts")
from bacula_del_catalog_jobids_conf import dry_run, query
from general_conf import db_host, db_user, db_name, services


def del_from_catalog(ji):
    """Deletes jobs from catalog by given list of job ids."""
    for x, y in ji:
        log.info("Deleting jobid %s from catalog. %s" % (x, y))
        if not dry_run:
            p1 = Popen(['echo', 'delete jobid=%s yes' % x], stdout=PIPE)
            p2 = Popen(['bconsole'], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            log.info("out %s, err %s" % (out, err))


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
        cur = con.cursor()
        cur.execute(query)
        del_jobids = cur.fetchall()
    except Exception as e:
        print(format_exception(e))
    del_from_catalog(del_jobids)
