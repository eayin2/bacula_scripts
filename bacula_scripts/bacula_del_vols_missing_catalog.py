#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-failed-jobs.py

Delete all volumes that have no job entries in the catalog anymore.

NO CONFIG NEEDED
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
from bacula_scripts.bacula_parser import bacula_parse

storages_conf_parsed = bacula_parse("bareos-dir")
sd_conf_parsed = bacula_parse("bareos-sd")


def has_catalog_entry(volume_name):
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute("SELECT * FROM media WHERE volumename=%s", (volume_name,))
        res = cur.fetchall()
        if len(res) > 0:
            return True
        else:
            return False
    except Exception as e:
        log.error(format_exception(e))
        return None


def run(storage_dir, dry_run=True):
    systemd_services_up(services)
    for volume in os.listdir(storage_dir):
        if not has_catalog_entry(volume):
            fn = os.path.join(storage_dir, volume)
            print("Delete %s" % fn)
            if not dry_run:
                os.remove(fn)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", help="Specify directory to be scanned for vols without catalog entry")
    p.add_argument("-dry", action="store_true", help="Dry run, simulates deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(args.d, dry_run=True)
    if args.d and not args.dry:
        run(args.d, dry_run=False)
