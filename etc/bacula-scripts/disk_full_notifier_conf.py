""" disk-full-notifier.py

Scan all devices in /dev and use the given default_limit, that is % of the used disk space, to
determine whether a disk the disk limit is reached and a warning mail should be send out.
You can use the list of custom_disk tuples (diskname, limit-number) to define individual limits
for the devices.
You can define the configuration values "default_limit" and "custom_disk" in the config.

CONFIG: /etc/bacula_scripts/disk_full_notifier.conf
"""
CUSTOM_DISKS = [("/dev/md1", 80), ("/dev/md2", 90)]
