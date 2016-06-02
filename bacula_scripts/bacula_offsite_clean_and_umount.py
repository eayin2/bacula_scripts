#!/usr/bin/python3
""" bacula_offsite_clean_and_umount.py
Deps: helputils

Prerequisites:
- Check in /etc/passwd where baculas home dir is (usually /var/lib/bacula) and add setup ssh keys there.
  E.g.:
  1. `mkdir /var/lib/bacula./.ssh`
  2. Then copy the ssh keys and config to the new home dir and also chown bacula:bacula them.
  3. Finally change owner: `chown -R bacula:bacula /var/lib/bacula/.ssh`
- Make sure to setup "sudo NOPASSWD" for the ssh user on the system where you plug in the offsite hdd,
  because umounting requires root access. Using setuid is less secure and root even more, so nopasswd may be the
  safest solution.
- If you installed this script via pip, then the bacula-scripts should be installed in /usr/bin, else things may not
  work fine.

Description:
Runs bacula-del-purged-vols.py to remove possibly existing purged vols while the offsite
disk is still mounted. When done it runs 'offsite-udev-bareos.py umount' either with or without
ssh (depends what args you give this script) to finally umount the offsite disk.
This script is meant to 'Run After Job' within a copy job resource. E.g.:
Run After Job = "/usr/local/bin/clean-and-umount-offsite-bacula.py phpc01.ffm01."
"""
import sys
from subprocess import Popen, PIPE

from helputils.core import log
sys.path.append("/etc/bacula-scripts")
from bacula_offsite_clean_and_umount_conf import del_purged_vols_bacula_bin, offsite_udev_bacula_bin


def main():
    p1 = Popen([del_purged_vols_bacula_bin], stdout=PIPE, stderr=PIPE)
    log.info(p1.communicate())


# Omitting umounting because copy job create a job for each backup it finds to copy to, so offsite disk has to be
# mounted.
# cmd = ["sudo", offsite_udev_bacula_bin, "umount"]
# cmd = (["ssh", "-oStrictHostKeyChecking=no", sys.argv[1]] + cmd) if len(sys.argv) == 2 else cmd
# p2 = Popen(cmd, stdout=PIPE, stderr=PIPE)
# log.info(p2.communicate())
