#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula_find_backups_bls.py

Find the on-disk volume inside a backup directory by parsing the volume information with `bls`
to match a client or fileset.

CONFIG: /etc/bacula-scripts/bacula_find_backups_bls_conf.py
"""
import argparse
import os
import re
import sys
import time
import traceback
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2
sys.path.append("/etc/bacula-scripts")
import bacula_find_backups_bls_conf as conf_mod


def CONF(attr):
    return getattr(conf_mod, attr, None)


def parse_vol(volume):
    """Parses volume with bls and returns jobname and timestamp of job."""
    cmd = ['timeout', '0.04', 'bls', volume, '-jv']
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    out = str(out)
    vol = os.path.basename(volume)
    try:
        cn = re.search('\\\\nClientName\s+:\s(.*?)\\\\n', out).group(1)
        fn = re.search('\\\\nFileSet\s+:\s(.*?)\\\\n', out).group(1)
        jl = re.search('\\\\nJobLevel\s+:\s(.*?)\\\\n', out).group(1)
        ti = re.search('\\\\nDate written\s+:\s(.*?)\\\\n', out).group(1)
    except:
        print("No metadata found: %s " % vol)
        return
    if CONF('FIND_FILESET'):
        if CONF('FIND_CLIENT') == cn and CONF('FIND_FILESET') == fn:
            print('(Parsed vol) cn: {0}, fn: {1}, jl: {2}, ti: {3}, vol: {4}'.format(cn, fn, jl, ti, vol))
    else:
        if CONF('FIND_CLIENT') == cn:
            print('(Parsed vol) cn: {0}, fn: {1}, jl: {2}, ti: {3}, vol: {4}'.format(cn, fn, jl, ti, vol))
    dt = datetime.strptime(ti, '%d-%b-%Y %H:%M')
    ts = time.mktime(dt.timetuple())
    return (cn, fn, ts, jl)


def run():
    for root, dirs, files in os.walk(CONF('FIND_BACKUP_DIR')):
        for file in files:
            parse_vol(os.path.join(root, file))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "-f",
        action="store_true",
        help="Find disk volumes matching a client or fileset inside a backup directory"
    )
    args = p.parse_args()
    if args.f:
        run()
