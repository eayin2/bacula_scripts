## bacula_scripts

This package comes with various bacula and bareos compatible scripts. Scripts were mainly tested
with bareos.

#### Install
You can install this package with `pip3 install bacula_scripts`
Python dependencies: helputils, gymail, psycopg2, lark-parser
Distro dependencies: Both bacula and bareos come with the tool `bls`, i.e. install
`bacula-tools` or `bareos-tools` on your distro.

#### Configuration
See the example configs in etc/bacula_scripts and modify for your needs. general_conf.py is
used by multiple scripts.


#### Usage


##### usage: bacula_stats [-h] [-a] [-r] [--version]
optional arguments:
  -h, --help    show this help message and exit
  -a, --all     Return all backups.
  -r, --recent  Return recent backups
  --version     show program's version number and exit




#### usage: bacula_del_purged_vols [-h] [-d] [-dry]

 bacula-del-purged-vols.py

Remove volumes and catalog entries for backups that have been marked 'Purged' based on the
deletion rules.

Deletion rules:
- Don't delete full if there are unpurged (=dependent, =unpruned) incrementals or diffs or less
  than four fulls.
- Don't delete diff if there are dependent incrementals or less than two diffs.
- Don't delete incremental if there are still dependent incrementals in the incremental chain.
  Latter should enforce that incremental backups within a chain are deleted all at once.
  This script will also work for remote storage daemons, provided that you setup the SSH alias
  in /root/.ssh/config with the same hostname that you defined for the "Address" (=hostname) in
  storages.conf.

Why this script?
We want to remove purged backups for disk space, scaling reason, but we don't want to delete all
backups that have been marked as 'Purged', because if you don't do backups for a very long time,
and have set 'AutoPrune = yes', plus your Retention is due, then important backups get deleted.
Also if you delete a full backup, which has been marked 'purged', but still have incremental
backups dependent on it, then you'll have a broken incremental backup chain.

Developing notes:
(1) We have to get the jobname and backup time from the volume file with bls, because purged
volumes dont have any job
    entries in the catalog anymore.
(2) Notice that we use the clientname and filesetname to check a backup chain for consistency,
because the jobname
    doesn't distinctively display all backups of a backup chain. Instead bacula uses all fileset
    and client name
    pairs.
(3) Not using paramiko in this script because we need `sudo` commands sometimes which we allowed
with %nopasswd% for the
    user.

User notes:
(1) We dont want to have purged vols recycled/overwritten automatically. because it can happen
    that we dont do a backup for a very long time and then we'd overwrite purged vols that had
    old backups that would could still needed and leave us with no backups at all. Instead our
    autorm script handles when to delete purged vols.
    => Make sure to set `Recycle = No` in bacula configs.
(2) After you changed Recycle to 'No' you may still have previous volumes marked with
    'Recycle = Yes'. To make all volumes in your database afterwards non recycable use this
    query in your db backend:
    `UPDATE media SET recycle=0;`
(3) Use `DRY_RUN = True` to simulate this script.
(4) If you use an external SD, make sure to setup SSH accordingly.
    IMPORTANT! Notice that this script assumes your '~/.ssh/config' uses the exact same FQDN
    as provided in the 'Address' directive of /etc/bacula/bacula.dir.d/storages.conf for the SSH
    host alias.
(5) For copy jobs provide the unique 'mediatype' of the copy jobs storage, so that the
    script won't use the 'JobLevel' from the parsed volume. We parse with the tool `bls`
    and check if we find a hint of `bls` output in the 'PoolName' of the JobLevel.
    This implies that you have to name your volumes with the appropriate joblevel. That is
    e.g. "Full-Pool" or "my-full-pool" or "inc-copy-pool" or "incremental-copy-pool".
    This workaround is required, because bacula writes the wrong job level to the volume's
    metadata. In the catalog it's correct, just not in the volume's metadata, where it always
    claims that the joblevel is 'I' for incremental. So our script's deletion algorithm wouldn't
    work, therefore in that case we need to know the job level to decide if a volume can't be
    deleted.
(6) For remote storage daemons setup the ssh config like this for example:
      Host phpc01e.ffm01.
      Hostname phpc01e.ffm01.
      Port 22
      IdentityFile ~/.ssh/id_phpc01_ed25519
      IdentitiesOnly yes
      User someuser
      ConnectTimeout=5

    # SUDOERS vs root SSH
    Now also make sure that you add following commands for the SSH user in sudoers with
    NOPASSWD or just SSH to root@your.host! Here we assume you created a user named
    bareos01 on the remote host that runs bacula-sd/bareos-sd. This example is for bareos on
    Ubuntu, your system paths may be different. Use `type bareos-sd`, `type timeout`.., to check
    their paths. Example:
      bareos01 ALL=NOPASSWD: /usr/sbin/bareos-sd -xc
      bareos01 ALL=NOPASSWD: /usr/sbin/bareos-dir -xc
      bareos01 ALL=NOPASSWD: /usr/bin/timeout 0.1 /usr/sbin/bls -jv *
      bareos01 ALL=NOPASSWD: /bin/rm /mnt/8tb01/offsite01/*

CONFIG: /etc/bacula-scripts/bacula_del_purged_vols_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Remove purged jobs from catalog and disk
  -dry        Simulate deletion




##### usage: bacula_del_jobs [-h] [-d] [-dry]
WARNING! Use with caution.

Delete all catalog entries that are associated to the given storage_name and their volume file
on the disk. Delete volumes that match the storage name or the job names.
Run this script only when you really want to delete something specifically.
This script doesn't work with remote storage devices.

If you need to remove backups from your dropbox encfs storage, then mount the encfs
storage. Use: `/usr/bin/bacula_encfs_backup mount`, which mounts it for example to /mnt/b01,
see /etc/bacula-scripts/bacula_encfs_backup_conf.py. bacula-del-jobs.py will then also remove
backups from /mnt/b01. Important! Unmount it afterwards, because the bacula user can't unmount
other users mountpoints.

If you use passphrases for your remote clients, run `ssh-add -t 10m /path/to/your/ssh/key`
before this script, else you'd get prompted repeatedly for the passphrase.

CONFIG: /etc/bacula_scripts/bacula_del_jobs_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete jobs and storage files
  -dry        Simulate deletion




##### usage: bacula_del_media_orphans [-h] [-d] [-dry]
Delete all catalog entries, which backup volume doesn't exist anymore.

Removes catalog entries of inexistent volumes, you should run this better manually and not
recurring in cron, because if you accidently remove a volume and want to migrate from an offsite
backup, then the job entry would also be gone.

CONFIG: /etc/bacula-scripts/bacula_del_media_orphans_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete jobs and storage files
  -dry        Simulate deletion



##### usage: bacula_offsite_backup_age_watch [-h] [-c]
Check when the last offsite backup was performed and send a warning notification mail if the
backup is too old. Add a symlink to this script for example to cron.weekly.

CONFIG: /etc/bacula-scripts/bacula_offsite_backup_age_watch_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -c          Check backup age



##### usage: bacula_del_vols_missing_catalog [-h] [-d D] [-dry]
Delete all volumes that have no job entries in the catalog anymore.

NO CONFIG NEEDED

optional arguments:
  -h, --help  show this help message and exit
  -d D        Specify directory to be scanned for vols without catalog entry
  -dry        Dry run, simulates deletion



##### usage: bacula_del_failed_jobs_and_volume [-h] [-d] [-dry]
Delete all volumes that are associated to failed jobs in the catalog and on disk,
so that the disk space is not filled up with incomplete backups.

Developing notes:
Issuing delete twice, because running it just once some entries persisted.
Eventually redo tests by comparing catalog entries between each deletion.

Job Status Code meanings:
A Canceled by user
E Terminated in error

NO CONFIG NEEDED

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete all failed jobs associated volumes
  -dry        Dry run, simulates deletion



##### usage: bacula_add_client [-h] [-r] [-fd_fqdn FD_FQDN]
                         [-os_type {linux,windows}]
                         [-create_client_job CREATE_CLIENT_JOB]
                         [-create_client_copy_job CREATE_CLIENT_COPY_JOB]
                         [-dry_run]
Add a client with storage device to the bareos configs

*** Warning ***
1. Run this script only on the host of the bareos-director daemon, because it needs
   to edit bareos-director config files.
2. Before adding a client with this script, make sure you have configured
   Director resource in `bareos-sd.d/director/bareos-dir.conf` and
   Storage resource in `bareos-sd.d/storage/bareos-sd.conf`
   on your sd-daemon priorly, because you have to type in the sd daemon password
   from `bareos-sd.d/director/bareos-dir.conf` and the FQDN of the sd-daemon to
   this script's settings.
3. The script configures on the client's fd-daemon the "Client resource" inside
   bareos-fd.d/client/myself.conf with "client backup encryption" and creates
   the key and cert needed for it. If you don't want to use client backup encryption
   you'd have to alter the script to your needs, that is remove ssl key creation
   and the config string.
4. Create the SSL master key and cert before running this script
   That is:
   + mkdir -p /etc/bareos/certs
   + Create the SSL key
     `openssl genrsa -aes256 -out /etc/bareos/certs/master.key -passout stdin 4096`
   + Create the public cert
     `openssl req -new -key master.key -x509 -out /etc/bareos/certs/master.cert`
   - Don't merge key and cert. Only needed upon restore and then the key needs the
     passphrase removed
   + Consider storing the master key on a different secure location than on the
     bareos-dir.
5. Following files can be written to:
   bareos-dir.d/client/bareos-fd.conf
   bareos-dir.d/storage/File.conf
   bareos-sd.d/device/FileStorage.conf
6. Make sure all passwords you enter to bareos resources are quoted
7. This script does not configure storages. Do that manually

optional arguments:
  -h, --help            show this help message and exit
  -r                    Add client
  -fd_fqdn FD_FQDN      FQDN of the filedaemon you want to add to the director
  -os_type {linux,windows}
                        Specify your client's OS. Supported: linux or windows
  -create_client_job CREATE_CLIENT_JOB
                        Create a job for the client?
  -create_client_copy_job CREATE_CLIENT_COPY_JOB
                        Create a copy job for the client?
  -dry_run              Simulate deletion



##### usage: host_uptime_server [-h] [-r]
Listen on a TCP socket for a host's uptime echo, packed into a json dumps. The json dumps
contains optionally a 'last_backup' json key with the seconds of the last performed backup
as its value.

Send an email notification, if the host's last uptime echo or performed backup is too long ago.

Open the configured TCP port in your firewall. E.g:
`iptables -A INPUT -p tcp --dport 11337 -j ACCEPT`
Provided you have `iptables-persistent` installed:
`iptables-save > /etc/iptables/rules.v4`

CONFIG /etc/bacula-scripts/host_uptime_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -r          Run host_uptime server



##### usage: host_uptime_client [-h] [-r]
Connect to the host_uptime server and send a json dictionary to the echo server containing this
hosts FQDN and the date of the latest performed bacula backup.

CONFIG: /etc/bacula-scripts/host_uptime_client_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -r          Run host_uptime client



##### usage: disk_full_notifier [-h] [-d]
Scan all devices in /dev and use the given default_limit, that is % of the used disk space, to
determine whether a disk the disk limit is reached and a warning mail should be send out.
You can use the list of custom_disk tuples (diskname, limit-number) to define individual limits
for the devices.
You can define the configuration values "default_limit" and "custom_disk" in the config.

CONFIG: /etc/bacula_scripts/disk_full_notifier.conf

optional arguments:
  -h, --help  show this help message and exit
  -d          Look for full disks and eventually send out warning mail


---
Project initially created in 05/2016
