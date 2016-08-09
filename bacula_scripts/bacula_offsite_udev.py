#!/usr/bin/python3
"""
offsite-udev-bacula.py
#
Usage:
offsite-udev-bacula.py add /dev/sdXY  -  mounts and runs offsite backup
offsite-udev-bacula.py umount         -  umounts offsite disk
#
Deps/Required scripts/packages:
 - del-purged-vols-bacula.py (@bareos-dir) (later put bacula scripts into one pypa package)
 - clean-and-umount-offsite-bacula.py  (@bareos-dir)
 - gymail
 -  helputils

User notes/prerequisites:
- "systemd-udevd runs in its own file system namespace and by default mounts done within udev .rules do not
  propagate to the host. So add MountFlags=shared in /usr/lib/systemd/system/systemd-udevd.service under
  the section [Service], else you won't be able to use the mountpoint.
- If you connect the offsite hdd not on the system where bacula-dir is running, then make sure to add the ssh alias
  for the remote system where bacula-dir is running to /root/.ssh/config. Plus make sure to connect the first time
  manually to ssh, so you can accept the ssh fingerprint, else the script will hang.
- Create offsite sd, copy job and pool resources
- Set prune level for offsite pool to 6 months
- Create udev rule, e.g.:
  KERNEL=="sd?1", SUBSYSTEMS=="usb", ATTRS{serial}=="5000c5007b2f7395", SYMLINK+="8tb01",
  ACTION=="add", RUN+="/usr/local/bin/offsite-udev-bareos.py add %p"

You also need the script clean-and-umount-offsite-bacula.py (see deps above):
- Add to your copy job 'Run after job = clean-and-umount-offsite-bacula.py phpc01.ffm01.', where phpc01.ffm01.
  would be the ssh alias/hostname of the offsite sd. If none argument is given, then clean-and-umount-offsite-bacula.py
  assumes the hdd is locally mounted.

Dev script description:
- When usb hdd plugged in (udev action=ADDED) script does:
 . mkdir_p; mount device;
 . run job=copy_..|bconsole
- When job is done (run after job)
  (this is the easier way to let bacula tell us when the job is done)
 . Initiate del-purged-vols-bacula.py on the bacula-dir server-side (with or without ssh)
   with 'Run after Job = /usr/local/bin/phpc01-offsite-bacula.py' which runs:
   '/usr/local/bin/del-purged-vols-bacula.py; ssh phpc01.ffm01. offsite-udev-bareos.py umount'
 . umount mountpoint
 . success mail

Further dev notes:
- bacula recognizes sys.exit(1) as exit status msg, but we initiate the job anyways ourselfs so we
  dont need to cancle the job on failure anyways
"""
import grp
import os
import pwd
import sys
import traceback
from subprocess import Popen, PIPE

from gymail.core import send_mail
from helputils.core import mkdir_p, umount, mount, log, try_func
sys.path.append("/etc/bacula-scripts")
from bacula_offsite_udev_conf import mp, backup_dirs, ssh_alias, copy_jobs, chown_user, chown_group


def run_job(jn, ssh_hn=None):
    """Running given bacula job."""
    log.info("run_job with jobname %s: ssh: %s" % (jn, str(ssh_hn)))
    ssh = ["/usr/bin/ssh", ssh_hn]
    cmd = ["/usr/sbin/bconsole"]
    cmd = (ssh + cmd) if ssh_hn else cmd
    p1 = Popen(cmd, stdin=PIPE, stdout=PIPE)
    log.info(p1.communicate(input="run job={0} yes\n".format(jn).encode()))


def main():
    task = sys.argv[1]
    dev = "/dev/%s" % sys.argv[2] if len(sys.argv) > 2 else None
    log.info("offsiteudev: task: %s, dev: %s" % (task, dev))
    if task == "add" and dev:
        mkdir_p(mp)
        if mount(dev=dev, mp=mp):
            for x in backup_dirs:
                x = os.path.join(mp, x)
                mkdir_p(x)
                uid, gid = pwd.getpwnam(chown_user).pw_uid, grp.getgrnam(chown_group).gr_gid
                os.chown(x, uid, gid)
            log.info("Running job now")
            [try_func(run_job, x, ssh_alias) for x in copy_jobs]
            log.info("Run jobs: %s" % ", ".join(copy_jobs))
        else:
            msg = "Couldn't mount offsite hdd, thus offsite backup not initiated."
            log.error(msg)
            send_mail(event="error", subject=os.path.basename(__file__), message=msg)
    elif task == "umount":
        umount(mp)
        msg = "Offsite backup completed successfully."
        log.info(msg)
        send_mail(event="info", subject=os.path.basename(__file__), message=msg)
    log.info("Done")
