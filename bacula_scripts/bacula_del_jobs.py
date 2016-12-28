#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-jobs.py
Description:
Deletes all catalog entries that are associated to the given storage_name and also tries to delete the volume on
disk. Notice that it deletes volumes matching given storage name OR give job names.
This is only intended to run when you really want to delete something specifically. Doesn't work for remote storage
devices.

If you need to remove also backups from your dropbox encfs storage, then mount it e.g. simply with 
`/usr/bin/bacula_encfs_backup mount` (which mounts e.g. to /mnt/b01 depending on your
/etc/bacula-scripts/bacula_encfs_backup_conf.py configuration) and then bacula-del-jobs.py will also remove backups from
there. Important: Make sure unmount it afterwards again, because bacula user can't unmount other users mountpoints.
"""
import re
import os
import sys
import traceback
import time
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

from helputils.core import format_exception, find_mountpoint, systemd_services_up

sys.path.append("/etc/bacula-scripts")
from bacula_del_jobs_conf import dry_run, storagenames, storagenames_del_only_catalog_entries, jobnames, filters, starttime
from general_conf import db_host, db_user, db_name, sd_conf, storages_conf, services

placeholder = "%s"  # Building our parameterized sql command
jobnames_placeholders = ', '.join([placeholder] * len(jobnames))
storagenames_placeholders = ', '.join([placeholder] * len(storagenames))


def parse_conf(lines):
    parsed = []
    obj = None
    for line in lines:
        line, hash, comment = line.partition('#')
        line = line.strip()
        if not line:
            continue
        m = re.match(r'(\w+)\s*{', line)
        if m:
            # Start a new object
            if obj is not None:
                raise Exception('Nested objects!')
            obj = {'thing': m.group(1)}
            parsed.append(obj)
            continue
        m = re.match(r'\s*}', line)
        if m:
            # End an object
            obj = None
            continue
        m = re.match(r'\s*([^=]+)\s*=\s*(.*)$', line)
        if m:
            # An attribute
            key, value = m.groups()
            obj[key.strip()] = value.rstrip(';')
            continue
    return parsed


def build_volpath(volname, storagename, sd_conf_parsed, storages_parsed):
    """Looks in config files for device path and returns devicename joined with the volname."""
    for storage in storages_parsed:
        if storagename == storage['Name']:
            devicename = storage['Device']
            for device in sd_conf_parsed:
                if devicename == device['Name']:
                    volpath = os.path.join(device['Archive Device'], volname)
                    if (not find_mountpoint(device["Archive Device"]) == "/" or storagename in
                            storagenames_del_only_catalog_entries):
                        return volpath
                    else:
                        print("Device %s not mounted. Please mount it." % devicename)
                        return None


def del_backups(b):
    """Deletes list of backups from disk and catalog"""
    for x, y, volpath, z in b:
        volname = os.path.basename(volpath)
        print('Deleting jobid: %s jn: %s vol: %s' % (x, y, volpath))
        if not dry_run:
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


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
        cur = con.cursor()
        query = "select distinct j.jobid, j.name, m.volumename, s.name from job j, media m, jobmedia jm, storage s " \
                "WHERE m.mediaid=jm.mediaid " \
                "AND j.jobid=jm.jobid " \
                "AND s.storageid=m.storageid "
        if filters == "jobname":
            data = jobnames
            query = query + " AND j.name IN (%s);" % (jobnames_placeholders)
        elif filters == "or_both":
            data = storagenames + jobnames
            query = query + " AND (s.name IN (%s) OR j.name IN (%s));" % (storagenames_placeholders,
                                                                          jobnames_placeholders)
        elif filters == "and_both":
            data = storagenames + jobnames
            query = query + " AND (s.name IN (%s) OR j.name IN (%s));" % (storagenames_placeholders,
                                                                          jobnames_placeholders)
        elif filters == "storage":
            data = storagenames
            query = query + " AND s.name IN (%s);" % (storagenames_placeholders)
        elif filters == "newer_than_starttime":
            data = starttime
            query = query + " AND j.starttime >= %s::timestamp;"
        elif filters == "older_than_starttime":
            data = starttime
            query = query + " AND j.starttime <= %s::timestamp;"
        else:
            log.error("Wrong filter or filter not defined.")
            sys.exit()
        print("Query: %s %s" % (query, str(data)))
        print(query % str(data))
        cur.execute(query, data)
        del_job_media_jm_storage = cur.fetchall()
    except Exception as e:
        print(format_exception(e))
    with open(sd_conf, 'r') as f:
        sd_conf_parsed = parse_conf(f)
    with open(storages_conf, 'r') as f:
        storages_conf_parsed = parse_conf(f)
    del_job_media_jm_storage = [(w, x, build_volpath(y, z, sd_conf_parsed, storages_conf_parsed), z) for w, x, y, z in
                                del_job_media_jm_storage if build_volpath(y, z, sd_conf_parsed, storages_conf_parsed)]
    del_backups(del_job_media_jm_storage)
