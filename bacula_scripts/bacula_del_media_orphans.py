#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-media-orphans.py
Description:
Deletes all associated catalog entries of those media entries, which backup volume doesn't exist anymore.
Set dry_run = True to print orphanned entries without deleting them, else set dry_run=False.
"""
import re
import os
import sys
import traceback
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

from helputils.core import (format_exception, find_mountpoint, remote_file_content, _isfile, islocal, log,
                            systemd_services_up)
sys.path.append("/etc/bacula-scripts")
from bacula_del_media_orphans_conf import dry_run, del_orphan_log, verbose
from general_conf import db_host, db_user, db_name, sd_conf, storages_conf, services


def parse_conf(lines):
    parsed = []
    obj = None
    for line in lines:
        line, hash, comment = line.partition('#')
        line = line.strip()
        if not line:
            continue
        m = re.match(r"(\w+)\s*{", line)
        if m:
            # Start a new object
            if obj is not None:
                raise Exception("Nested objects!")
            obj = {'thing': m.group(1)}
            parsed.append(obj)
            continue
        m = re.match(r"\s*}", line)
        if m:
            # End an object
            obj = None
            continue
        m = re.match(r"\s*([^=]+)\s*=\s*(.*)$", line)
        if m:
            # An attribute
            key, value = m.groups()
            obj[key.strip()] = value.rstrip(';')
            continue
    return parsed


def main():
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host)
        cur = con.cursor()
        cur.execute("SELECT m.volumename, s.name FROM media m, storage s WHERE m.storageid=s.storageid;")
        media_storage = cur.fetchall()  # e.g. [('Incremental-ST-0126', 's8tb01'), ('Full-ST-0031', 's8tb01'), ..]
    except Exception as e:
        print(format_exception(e))
    with open(storages_conf, "r") as myfile:
        storages_conf_parsed = parse_conf(myfile)
    for volname, storagename in media_storage:
        for storage in storages_conf_parsed:
            hn = storage["Address"]
            if not islocal(hn):
                remote_sd_conf = remote_file_content(hn, sd_conf)
                sd_conf_parsed = parse_conf(remote_sd_conf)
            else:
                with open(sd_conf, "r") as myfile:
                    sd_conf_parsed = parse_conf(myfile)
            if storagename == storage["Name"]:
                devicename = storage["Device"]
                for device in sd_conf_parsed:
                    if devicename == device["Name"]:
                        volpath = os.path.join(device["Archive Device"], volname)
                        if verbose:
                            log.debug("hn: %s" % hn)
                        if not find_mountpoint(device["Archive Device"], hn) == "/":
                            if not _isfile(volpath, hn):
                                log.info("Deleted volume %s from catalog, because file doesn't exist." % volpath)
                                with open(del_orphan_log, 'a') as f:
                                    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    f.write("{0} {1}\n".format(time, volpath))
                                if not dry_run:
                                    p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
                                    p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
                                    p1.stdout.close()
                                    out, err = p2.communicate()
                                    log.debug("out: %s, err: %s" % (out, err))
                            elif verbose is True:
                                log.info('File exists for %s' % volpath)
