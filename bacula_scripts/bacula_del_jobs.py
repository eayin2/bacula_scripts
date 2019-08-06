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
try:
    clients_placeholders = ', '.join([placeholder] * len(CONF('DEL_CLIENTS')))
except:
    CONF_SET('DEL_CLIENTS', None)
try:
    filesets_placeholders = ', '.join([placeholder] * len(CONF('DEL_FILESETS')))
except:
    CONF_SET('DEL_FILESETS', None)
try:
    filesets_not_placeholders = ', '.join([placeholder] * len(CONF('DEL_NOT_FILESETS')))
except:
    CONF_SET('DEL_NOT_FILESETS', None)
try:
    jobnames_placeholders = ', '.join([placeholder] * len(CONF('DEL_JOB_NAMES')))
except:
    CONF_SET('DEL_JOB_NAMES', None)
try:
    storagenames_placeholders = ', '.join([placeholder] * len(CONF('DEL_STORAGE_NAMES')))
except:
    CONF_SET('DEL_STORAGE_NAMES', None)


def build_volpath(volname, storagename, sd_conf_parsed, storages_parsed):
    """Looks in config files for device path and returns devicename joined with the volname."""
    try:
        device = storages_parsed["Storage"][storagename]["Device"]
    except:
        return None
    if device:
        try:
            ad = sd_conf_parsed["Device"][device]["ArchiveDevice"]
        except:
            ad = None
        if not ad:
            # Add Autochanger support 10/2018
            try:
                autochanger = sd_conf_parsed["Autochanger"][device]["ArchiveDevice"]
            except:
                return None
            if autochanger:
                # Just get first virtual device, because autochanger device should have the same
                # archive device anyways
                device = autochanger.split(",")[0].strip()
                ad = sd_conf_parsed["Device"][device]["ArchiveDevice"]
    if ad:
        volpath = os.path.join(ad, volname)
        if (not find_mountpoint(ad) == "/" or storagename in CONF('DEL_STORAGE_NAMES_CATALOG')):
            return volpath
    if not device and not ad:
        return None


def del_backups(b):
    """Deletes list of backups from disk and catalog"""
    for jobid, jobname, volname, volpath in b:
        volname = os.path.basename(volpath)
        print("Deleting jobid: %s jn: %s vol: %s" % (jobid, jobname, volpath))
        if CONF('DRY_RUN'):
            print("--- Dry run ---")
        else:
            print("--- Initiate deletion ---")
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


def run(args):
    if args.dry_run:
        CONF_SET('DRY_RUN', args.dry_run)
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
        #if all([False] if not CONF('DEL_CLIENTS') else CONF('DEL_CLIENTS')):
        if CONF('DEL_CLIENTS') and all(CONF('DEL_CLIENTS')):
            data += CONF('DEL_CLIENTS')
            query2 = "j.clientid IN (SELECT clientid FROM client WHERE name IN (%s))" % clients_placeholders
            query += operator2 + query2
        if CONF('DEL_FILESETS') and all(CONF('DEL_FILESETS')):
            data += CONF('DEL_FILESETS')
            query2 = "j.filesetid IN (SELECT filesetid FROM fileset WHERE fileset IN (%s))" % filesets_placeholders
            query += operator2 + query2
        if CONF('DEL_NOT_FILESETS') and all(CONF('DEL_NOT_FILESETS')):
            data += CONF('DEL_NOT_FILESETS')
            query2 = "j.filesetid NOT IN (SELECT filesetid FROM fileset WHERE fileset IN (%s))" % filesets_not_placeholders
            query += operator2 + query2
        if CONF('DEL_JOB_NAMES') and all(CONF('DEL_JOB_NAMES')):
            data += CONF('DEL_JOB_NAMES')
            query2 = "j.name IN (%s)" % jobnames_placeholders
            query += operator2 + query2
        if CONF('DEL_STORAGE_NAMES') and all(CONF('DEL_STORAGE_NAMES')):
            data += CONF("DEL_STORAGE_NAMES")
            query2 = "s.name IN (%s)" % storagenames_placeholders
            query += operator2 + query2
        if CONF('DEL_NEWER') and all(CONF('DEL_NEWER')):
            data += CONF('DEL_NEWER')
            query += operator2 + "j.starttime >= %s::timestamp"
        if CONF('DEL_OLDER') and all(CONF('DEL_OLDER')):
            data += CONF('DEL_OLDER')
            query += operator2 + "j.starttime <= %s::timestamp"
        print("Query: %s %s" % (query, str(data)))
        directives = ["DEL_CLIENTS", "DEL_JOB_NAMES", "DEL_STORAGE_NAMES", "DEL_NEWER"]
        if all(CONF(directive) is None for directive in directives):
            print("No deletion rule configured. Exiting")
            sys.exit()
        query += ";"
        cur.execute(query, data)
        select_job_media_jm_storage = cur.fetchall()
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

    del_job_media_jm_storage = list()
    for jobid, jobname, volname, storagename in select_job_media_jm_storage:
        if build_volpath(volname, storagename, sd_conf_parsed, storages_conf_parsed):
            storage_path = build_volpath(
                volname,
                storagename,
                sd_conf_parsed,
                storages_conf_parsed
            )
            print("Storage found: %s" % storage_path)
            del_job_media_jm_storage.append(
                (
                    jobid,
                    jobname,
                    volname,
                    build_volpath(
                        volname,
                        storagename,
                        sd_conf_parsed,
                        storages_conf_parsed
                    )
                )
            )
        elif args.default_storage:
            print("Storage not found. Specified default_storage: %s" % args.default_storage)
            del_job_media_jm_storage.append((jobid, jobname, volname, os.path.join(args.default_storage, volname)))
        elif args.force_del_catalog:
            # Setting path to None. This way only the catalog entry will be deleted
            print("Storage not found. force_del_catalog: True. Deleting catalog entries")
            del_job_media_jm_storage.append((jobid, jobname, volname, None))
        else:
            # Neither deleting file nor catalog
            print("Storage not found. Skipping")
            pass
    print("Deleting: %s" % del_job_media_jm_storage)
    del_backups(del_job_media_jm_storage)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete jobs and storage files")
    p.add_argument("-n", "--dry_run", action="store_true", help="Simulate deletion")
    p.add_argument(
        "--force_del_catalog",
        action="store_true",
        help="Delete the catalog entry even if no storage config was found in the storage config."
    )
    p.add_argument(
        "--default_storage",
        help="Specify a default storage location. Warning: Use this only if you know what you " \
        "are doing. This will build the volpath with the given default storage location. " \
        "If you reuse volumes and don't use volumes with unique labels, then you could " \
        "eventually remove a new backup which just uses the volume name of the old backup."
    )
    args = p.parse_args()
    run(args)
