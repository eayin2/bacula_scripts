#!/usr/bin/python3
"""disk-full-notifier.py

Scans the system for all connected devices (/dev/..) and use the given default_limit (% of the used disk space) to
determine whether to send out a warning mail, that the disk limit was reached. You can use the list of custom_disk
tuples (diskname, limit-number) to define individual. Limits for the devices.
You can define the configuration values "default_limit" and "custom_disk" in
/etc/bacula_scripts/disk_full_notifier.conf.
"""
import os
import subprocess
import sys

from gymail.core import send_mail
sys.path.append("/etc/bacula-scripts")
try:
    custom_disks = []
    from disk_full_notifier_conf import *
except:
    print("Info: Run disk_full_notifier without config")
    pass
default_limit = 95


def mounted_disks():
    df = subprocess.Popen(["df"], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    lines = filter(None, output.decode("utf-8").split("\n")[1:])
    for x in lines:
        fs, blocks, used, available, percent, mountpoint = x.split()
        if "/dev/" in fs:
            yield fs


def main():
    default_disks = [(x, default_limit) for x in mounted_disks() if x not in [y[0] for y in custom_disks]]
    for x, y in default_disks + custom_disks:
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
