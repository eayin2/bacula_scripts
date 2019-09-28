#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-media-orphans.py

Delete all catalog entries, which backup volume doesn't exist anymore.

Removes catalog entries of inexistent volumes, you should run this better manually and not
recurring in cron, because if you accidently remove a volume and want to migrate from an offsite
backup, then the job entry would also be gone.

CONFIG: /etc/bacula-scripts/bacula_del_media_orphans_conf.py
"""
import argparse
import os
import re
import sys
import traceback
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

from helputils.core import format_exception, find_mountpoint, remote_file_content, _isfile, islocal, systemd_services_up
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
import bacula_del_media_orphans_conf as conf_mod
from bacula_scripts.bacula_parser import bacula_parse
from general_conf import (
    BACULA_DIR_BIN,
    BACULA_SD_BIN,
    db_host,
    db_user,
    db_name,
    db_password,
    sd_conf,
    services,
    storages_conf
)


def CONF(attr):
    return getattr(conf_mod, attr, None)


def get_archive_device_of_device(device, sd_conf_parsed):
    if device:
        device2 = sd_conf_parsed["Device"][device]
        if device2:
            ad = device2["ArchiveDevice"]
            return ad
        elif not device2:
            devices2 = sd_conf_parsed["Autochanger"].get(device,None)
            if devices2:
                devices2 = devices2["Device"]
                if devices2:
                    dev = devices2.split(",")[0].strip()
                    ad = sd_conf_parsed["Device"][dev]["ArchiveDevice"]
                    return ad
    return None


def run(dry_run=False):
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute("SELECT m.volumename, s.name FROM media m, storage s WHERE m.storageid=s.storageid;")
        media_storage = cur.fetchall()  # e.g. [('Incremental-ST-0126', 's8tb01'), ('Full-ST-0031', 's8tb01'), ..]
    except Exception as e:
        print(format_exception(e))
    storages_conf_parsed = bacula_parse(BACULA_DIR_BIN)
    for volname, storagename in media_storage:
        for storage_name, storage_value in storages_conf_parsed["Storage"].items():
            hn = storage_value["Address"]
            if not islocal(hn):
                sd_conf_parsed = bacula_parse(BACULA_SD_BIN, hn=hn)
            else:
                sd_conf_parsed = bacula_parse(BACULA_SD_BIN)
            if storagename == storage_name:
                device = storage_value["Device"]
                ad = get_archive_device_of_device(device, sd_conf_parsed)
                if ad:
                    volpath = os.path.join(ad, volname)
                else:
                    continue
                if CONF('VERBOSE'):
                    log.debug("hn: %s" % hn)
                    if not find_mountpoint(ad, hn) == "/":
                        if not _isfile(volpath, hn):
                            log.info("Deleted volume %s from catalog, because file doesn't exist." % volpath)
                            with open(CONF('LOG'), 'a') as f:
                                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                f.write("{0} {1}\n".format(time, volpath))
                            if not dry_run or not CONF('DRY_RUN'):
                                p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
                                p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
                                p1.stdout.close()
                                out, err = p2.communicate()
                                log.debug("out: %s, err: %s" % (out, err))
                        elif CONF('VERBOSE') is True:
                            log.info('File exists for %s' % volpath)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Delete jobs and storage files")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    elif args.d and not args.dry:
        run(dry_run=False)
