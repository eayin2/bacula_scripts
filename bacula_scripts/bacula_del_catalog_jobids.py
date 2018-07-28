#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-catalog-jobids.py

WARNING: Use carefully!

Delete only the catalog entries, not the associated files, that are selected in configured SQL
query.

This script uses `echo delete jobid= | bconsole` to delete the selected jobids.

CONFIG: /etc/bacula-scripts/bacula_del_catalog_jobids_conf.py
"""
import argparse
import imp
import re
import os
import sys
import traceback
import time
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

from helputils.core import format_exception, systemd_services_up
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
import bacula_del_catalog_jobids_conf as conf_mod
from general_conf import db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


def CONF_SET(attr, val):
    return setattr(conf_mod, attr, val)


def del_from_catalog(ji):
    """Delete the given list of job ids from the catalog."""
    for x, y in ji:
        if not CONF('DRY_RUN'):
            log.info("Deleting jobid %s from catalog. %s" % (x, y))
            p1 = Popen(['echo', 'delete jobid=%s yes' % x], stdout=PIPE)
            p2 = Popen(['bconsole'], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            log.info("out %s, err %s" % (out, err))
        else:
            log.info("DRY_RUN = TRUE (SIMULATION) deleting jobid %s from catalog. %s" % (x, y))
            

def run():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute(CONF('QUERY'))
        del_jobids = cur.fetchall()
    except Exception as e:
        print(format_exception(e))
    del_from_catalog(del_jobids)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete the SQL selected list of jobids from catalog")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.dry:
        CONF_SET("DRY_RUN", True)
    if args.d:
        run()

