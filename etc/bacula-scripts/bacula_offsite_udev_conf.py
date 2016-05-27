# offsite-udev-bacula.py
#
# Usage:
# offsite-udev-bacula.py add /dev/sdXY  -  mounts and runs offsite backup
# offsite-udev-bacula.py umount         -  umounts offsite disk
#
# Deps/Required scripts/packages:
#  - del-purged-vols-bacula.py (@bareos-dir) (later put bacula scripts into one pypa package)
#  - clean-and-umount-offsite-bacula.py  (@bareos-dir)
#  - gymail
#  -  helputils
#
#
# User notes/prerequisites:
# - "systemd-udevd runs in its own file system namespace and by default mounts done within udev .rules do not
#   propagate to the host. So add MountFlags=shared in /usr/lib/systemd/system/systemd-udevd.service under
#   the section [Service], else you won't be able to use the mountpoint.
# - If you connect the offsite hdd not on the system where bacula-dir is running, then make sure to add the ssh alias
#   for the remote system where bacula-dir is running to /root/.ssh/config. Plus make sure to connect the first time
#   manually to ssh, so you can accept the ssh fingerprint, else the script will hang. 
# - Create offsite sd, copy job and pool resources
# - Set prune level for offsite pool to 6 months
# - Create udev rule, e.g.:
#   KERNEL=="sd?1", SUBSYSTEMS=="usb", ATTRS{serial}=="5000c5007b2f7395", SYMLINK+="8tb01",
#   ACTION=="add", RUN+="/usr/local/bin/offsite-udev-bareos.py add %p"
#
# You also need the script clean-and-umount-offsite-bacula.py (see deps above):
# - Add to your copy job 'Run after job = clean-and-umount-offsite-bacula.py phpc01.ffm01.', where phpc01.ffm01.
#   would be the ssh alias/hostname of the offsite sd. If none argument is given, then
#clean-and-umount-offsite-bacula.py
#   assumes the hdd is locally mounted.
#
# Dev script description:
# - When usb hdd plugged in (udev action=ADDED) script does:
#  . mkdir_p; mount device;
#  . run job=copy_..|bconsole
# - When job is done (run after job)
#   (this is the easier way to let bacula tell us when the job is done)
#  . Initiate del-purged-vols-bacula.py on the bacula-dir server-side (with or without ssh)
#    with 'Run after Job = /usr/local/bin/phpc01-offsite-bacula.py' which runs:
#                                               
#    '/usr/local/bin/del-purged-vols-bacula.py; ssh phpc01.ffm01. offsite-udev-bareos.py umount'         
#  . umount mountpoint
#  . success mail
#
# Further dev notes:
# - bacula recognizes sys.exit(1) as exit status msg, but we initiate the job anyways ourselfs so we
#   dont need to cancle the job on failure anyways
#
# Config:
mp = "/mnt/8tb01"
backup_dirs = ["offsite01"]
ssh_alias = "phserver01.ffm01."  # Leave empty if offsite disk is connected also on the bacula server
chown_user = "bareos"
chown_group = "bareos"
copy_jobs = ["c01full-lt-test01-phserver01", "c01diff-lt-test01-phserver01", "c01inc-lt-test01-phserver01"]
