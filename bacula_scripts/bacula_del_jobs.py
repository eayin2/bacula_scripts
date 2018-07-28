#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-jobs.py

WARNING! Use with caution.

Delete all catalog entries that are associated to the given storage_name and their volume file
on the disk. Delete volumes that match the storage name or the job names.
Run this script only when you really want to delete something specifically.
This script doesn't work with remote storage devices.

If you need to remove backups from your dropbox encfs storage, then mount the encfs
storage. Use: `/usr/bin/bacula_encfs_backup mount`, which mounts it for example to /mnt/b01,
see /etc/bacula-scripts/bacula_encfs_backup_conf.py. bacula-del-jobs.py will then also remove
backups from /mnt/b01. Important! Unmount it afterwards, because the bacula user can't unmount
other users mountpoints.

If you use passphrases for your remote clients, run `ssh-add -t 10m /path/to/your/ssh/key`
before this script, else you'd get prompted repeatedly for the passphrase.

CONFIG: /etc/bacula_scripts/bacula_del_jobs_conf.py
"""
import argparse
import os
import re
import sys
import time
import traceback
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2
from helputils.core import format_exception, find_mountpoint, systemd_services_up

sys.path.append("/etc/bacula-scripts")
import bacula_del_jobs_conf as conf_mod
from bacula_scripts.bacula_parser import bacula_parse
from general_conf import db_host, db_user, db_name, db_password, sd_conf, storages_conf, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


def CONF_SET(attr, val):
    return setattr(conf_mod, attr, val)


placeholder = "%s"  # Building our parameterized sql command
jobnames_placeholders = ', '.join([placeholder] * len(CONF('DEL_JOB_NAMES')))
storagenames_placeholders = ', '.join([placeholder] * len(CONF('DEL_STORAGE_NAMES')))


def build_volpath(volname, storagename, sd_conf_parsed, storages_parsed):
    """Looks in config files for device path and returns devicename joined with the volname."""
    for storage_name, storage_value in storages_parsed["Storage"].items():
        if storagename == storage_name:
            devicename = storage_value['Device']
            for device_name, device_value in sd_conf_parsed["Device"].items():
                if devicename == device_name:
                    volpath = os.path.join(device_value['ArchiveDevice'], volname)
                    if (not find_mountpoint(device_value["ArchiveDevice"]) == "/" or storagename in
                            CONF('DEL_STORAGE_NAMES_CATALOG')):
                        return volpath
                    else:
                        print("Device %s not mounted. Please mount it." % devicename)
                        return None


def del_backups(b):
    """Deletes list of backups from disk and catalog"""
    for x, y, volpath, z in b:
        volname = os.path.basename(volpath)
        print("Deleting jobid: %s jn: %s vol: %s" % (x, y, volpath))
        if not CONF('DRY_RUN'):
            try:
                os.remove(volpath)
                print("Deleted file %s" % volpath)
            except:
                print('Already deleted vol %s' % volpath)
            p1 = Popen(['echo', 'delete volume=%s yes' % volname], stdout=PIPE)
            p2 = Popen(['bconsole'], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            print(out, err)


def run(dry_run=False):
    if dry_run:
        CONF_SET('DRY_RUN', dry_run)
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        query = """
SELECT DISTINCT j.jobid, j.name, m.volumename, s.name
FROM job j, media m, jobmedia jm, storage s
WHERE m.mediaid=jm.mediaid
AND j.jobid=jm.jobid
AND s.storageid=m.storageid
"""
        data = []
        if CONF('OPERATOR').lower() == "or":
            operator2 = " OR "
        else:
            operator2 = " AND "
        if all(CONF('DEL_JOB_NAMES')):
            data += CONF('DEL_JOB_NAMES')
            query2 = "j.name IN (%s)" % jobnames_placeholders
            query += operator2 + query2
        if all(CONF('DEL_STORAGE_NAMES')):
            data += CONF("DEL_STORAGE_NAMES")
            query2 = "s.name IN (%s)" % storagenames_placeholders
            query += operator2 + query2
        if all(CONF('DEL_NEWER')):
            data += CONF('DEL_NEWER')
            query += operator2 + "j.starttime >= %s::timestamp"
        if all(CONF('DEL_OLDER')):
            data += CONF('DEL_OLDER')
            query += operator2 + "j.starttime <= %s::timestamp"
        print("Query: %s %s" % (query, str(data)))
        query += ";"
        cur.execute(query, data)
        del_job_media_jm_storage = cur.fetchall()
        print(del_job_media_jm_storage)
    except Exception as e:
        print(format_exception(e))
        print(
            "\n\nYour config /etc/bacula-scripts/bacula_del_jobs_conf.py has an error.\n"\
            "Check if all your configured values are in the tuple format. E.g.:\n"\
            "DEL_NEWER = ('',) and not DEL_NEWER = ('')"
        )
        return
    sd_conf_parsed = bacula_parse("bareos-sd")
    storages_conf_parsed = bacula_parse("bareos-dir")
    del_job_media_jm_storage = [
        (w, x, build_volpath(y, z, sd_conf_parsed, storages_conf_parsed), z) for w, x, y, z in
        del_job_media_jm_storage if build_volpath(y, z, sd_conf_parsed, storages_conf_parsed)
    ]
    del_backups(del_job_media_jm_storage)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete jobs and storage files")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    elif args.d and not args.dry:
        run(dry_run=False)
