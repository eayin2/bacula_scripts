#!/usr/bin/python3
# -*- coding: utf-8 -*-
# bacula_find_backups_bls.py
import re
import os
import sys
import traceback
import time
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2

sys.path.append("/etc/bacula-scripts")
from bacula_find_backups_bls_conf import backup_dir, client, fileset


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
    if fileset:
        if client == cn and fileset == fn:
            print('(Parsed vol) cn: {0}, fn: {1}, jl: {2}, ti: {3}, vol: {4}'.format(cn, fn, jl, ti, vol))
    else:
        if client == cn:
            print('(Parsed vol) cn: {0}, fn: {1}, jl: {2}, ti: {3}, vol: {4}'.format(cn, fn, jl, ti, vol))
    dt = datetime.strptime(ti, '%d-%b-%Y %H:%M')
    ts = time.mktime(dt.timetuple())
    return (cn, fn, ts, jl)


def main():
    for root, dirs, files in os.walk(backup_dir):
        for file in files:
            parse_vol(os.path.join(root, file))
