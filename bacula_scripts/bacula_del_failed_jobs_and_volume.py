#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-failed-jobs.py

Delete all volumes that are associated to failed jobs in the catalog and on disk,
so that the disk space is not filled up with incomplete backups.

Developing notes:
Issuing delete twice, because running it just once some entries persisted.
Eventually redo tests by comparing catalog entries between each deletion.

Job Status Code meanings:
A Canceled by user
E Terminated in error

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
from general_conf import (
    BACULA_DIR_BIN,
    BACULA_SD_BIN,
    db_host,
    db_name,
    db_password,
    db_user,
    services,
    ARCHIVE_DEVICE
)
from bacula_scripts.bacula_parser import bacula_parse

storages_conf_parsed = bacula_parse(BACULA_DIR_BIN)
sd_conf_parsed = bacula_parse(BACULA_SD_BIN)

def get_archive_device_of_device(device):
    """
    2021-05 Deprecated - specify path manually. Deprecated, because would need to parse
    autochanger for device name, then get each autochanger device and check if the volume
    is in one of the autochanger archive device paths. Those are just 3-4 lines of code,
    but it's not needed for this setup. Keep it simple and just specify the archive device
    manually where to look at. In this setup there won't be any redundant file names, so
    it's safe to do.
    """
    sd_conf_parsed = bacula_parse(BACULA_SD_BIN)
    if device:
        device2 = sd_conf_parsed["Device"][device]
        print("devdev: %s" % device)
        print(sd_conf_parsed["Device"])
        print("dev2: %s" % device2)
        if device2:
            ad = device2["ArchiveDevice"]
            return ad
        elif not device2:
            try:
                device2 = sd_conf_parsed["Autochanger"][device]["Device"]
            except:
                return None
            if device2:
                device2 = autochanger["Device"].split(",")[0].strip()
                ad = sd_conf_parsed["Device"][device2]["ArchiveDevice"]
                return ad
    return None


def get_archive_device_of_job(jobname):
    """deprecated"""
    job = storages_conf_parsed["Job"].get(jobname, None)
    if job:
        storage = job["Storage"]
        device = storages_conf_parsed["Storage"].get(storage, None)
        device = device["Device"]
        return get_archive_device_of_device(device)
    return None


def get_archive_device_of_pool(poolname):
    """deprecated"""
    storage = storages_conf_parsed["Pool"]["Storage"]
    device = storages_conf_parsed["Storage"][storage]["Device"]
    return get_archive_device_of_device(device)


def get_volpath(jname, volname):
    """deprecated"""
    archive_device = get_archive_device_of_job(jname)
    print(archive_device)
    if not archive_device:
        return None
    volpath = os.path.join(archive_device, volname)
    if os.path.isfile(volpath):
        return volpath
    else:
        for pool_name, pool_value in storages_conf_parsed["Pool"].items():
            archive_device = get_archive_device_of_pool(pool_name)
            if archive_device:
                volpath = os.path.join(archive_device, volname)
                if os.path.isfile(volpath):
                    return volpath
    return None


def del_catalog(volname, jobid):
    p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
    p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
    p1.stdout.close()
    out, err = p2.communicate()
    p1 = Popen(["echo", "delete volume=%s yes" % jobid], stdout=PIPE)
    p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
    p1.stdout.close()
    out, err = p2.communicate()
    log.debug("out: %s, err: %s" % (out, err))


def run(dry_run=True):
    print("Dry run: %s" % dry_run)
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute("SELECT DISTINCT j.name, j.jobid, m.volumename FROM job j, jobmedia jm, "
                    "media m WHERE j.JobStatus "
                    "IN ('E', 'A', 'f', 't', 's') AND j.jobid=jm.jobid AND jm.mediaid=m.mediaid "
                    "AND j.realendtime < NOW() - INTERVAL '4 days';")
        # Selecting older than 30 days, so that running jobs won't be selected
        failed_job_jm_media = cur.fetchall()
    except Exception as e:
        log.error(format_exception(e))
    for jname, jobid, volname in failed_job_jm_media:
        # deprecated 2021-05
        # volume_path = get_volpath(jname, volname)        
        volume_path = os.path.join(ARCHIVE_DEVICE, volname)
        log.info("Deleting catalog entries for job (id: %s, volname: %s)." % (jobid, volname))
        if not dry_run:
            print("volume_path: %s" % volume_path)
            if not volume_path:
                print("No volume path. Try to delete with bacula_del_orphanned")
            if volume_path:
                log.info("Removing volume from disk %s" % volume_path)
                os.remove(volume_path)
                del_catalog(volname, jobid)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete all failed jobs associated volumes")
    p.add_argument("-dry", action="store_true", help="Dry run, simulates deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    if args.d and not args.dry:
        run(dry_run=False)
