#!/usr/bin/python3
""" disk-full-notifier.py

Scan all devices in /dev and use the given default_limit, that is % of the used disk space, to
determine whether a disk the disk limit is reached and a warning mail should be send out.
You can use the list of custom_disk tuples (diskname, limit-number) to define individual limits
for the devices.
You can define the configuration values "default_limit" and "custom_disk" in the config.

CONFIG: /etc/bacula_scripts/disk_full_notifier.conf
"""
import argparse
import os
import subprocess
import sys
from argparse import RawDescriptionHelpFormatter

from gymail.core import send_mail
sys.path.append("/etc/bacula-scripts")
import disk_full_notifier_conf as conf_mod


def CONF(attr):
    return getattr(conf_mod, attr, None)


def CONF_SET(attr, val):
    return setattr(conf_mod, attr, val)


if not CONF('CUSTOM_DISKS'):
    CONF_SET('CUSTOM_DISKS', [])
default_limit = 95


def mounted_disks():
    df = subprocess.Popen(["df"], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    lines = filter(None, output.decode("utf-8").split("\n")[1:])
    for x in lines:
        fs, blocks, used, available, percent, mountpoint = x.split()
        if "/dev/" in fs:
            yield fs


def run():
    default_disks = [(x, default_limit) for x in mounted_disks() if x not in [y[0] for y in CONF('CUSTOM_DISKS')]]
    for x, y in default_disks + CONF('CUSTOM_DISKS'):
        df = subprocess.Popen(["df", x], stdout=subprocess.PIPE)
        output = df.communicate()[0]
        fs, blocks, used, available, percent, mountpoint = output.decode("utf-8").split("\n")[1].split()
        used_percent = int(percent.strip("%"))
        if used_percent > y:
            msg = "%s\tWarning: %s%% used (limit: %s%%). Sending notifcation mail" % (x, used_percent, y)
            print(msg)
            send_mail(event="error", subject=os.path.basename(__file__), message=msg)
        else:
            print("%s\tOkay: %s%% used (limit: %s%%)" % (x, used_percent, y))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument(
        "-d",
        action="store_true",
        help="Look for full disks and eventually send out warning mail"
    )
    args = p.parse_args()
    if args.d:
        run()
