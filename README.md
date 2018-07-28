## bacula_scripts

This package comes with various bacula and bareos compatible scripts. Scripts were mainly tested
with bareos.

#### Install
You can install this package with `pip3 install bacula_scripts`
Python dependencies: helputils, gymail, psycopg2, lark-parser
Distro dependencies: Both bacula and bareos come with the tool `bls`, i.e. install
bacula-/bareos-tools on your distro.

#### Configuration
See the example configs in etc/bacula_scripts and modify for your needs. general_conf.py is
used by multiple scripts.


#### List of scripts

##### usage: bacula_db_backup [-h] [-d D] [-c C] [-p P] -t
                        {postgresql,mongodb,mysql}

optional arguments:
  -h, --help            show this help message and exit
  -d D                  Delete a db dump backup.
  -c C                  Create a db dump backup.
  -p P                  Directory where the db dump should be stored.
  -t {postgresql,mongodb,mysql}
                        Choose the db type


##### usage: bacula_del_catalog_jobids [-h] [-d] [-dry]
bacula-del-catalog-jobids.py WARNING: Use carefully! Delete only the catalog
entries, not the associated files, that are selected in configured SQL query.
This script uses `echo delete jobid= | bconsole` to delete the selected
jobids. CONFIG: /etc/bacula-scripts/bacula_del_catalog_jobids_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete the SQL selected list of jobids from catalog
  -dry        Simulate deletion


##### usage: bacula_del_failed_jobs [-h] [-d] [-dry]
bacula-del-failed-jobs.py Delete all volumes that are associated to failed
jobs. Developing notes: Issuing delete twice, because running it just once
some entries persisted. Eventually redo tests by comparing catalog entries
between each deletion. Job Status Code meanings: A Canceled by user E
Terminated in error NO CONFIG NEEDED

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete all failed jobs associated volumes
  -dry        Dry run, simulates deletion


##### usage: bacula_del_jobs [-h] [-d] [-dry]
Delete catalog entries and associated volumes from disk, based on configured
settings in/etc/bacula_scripts/bacula_del_jobs_conf.py.

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete jobs and storage files
  -dry        Simulate deletion


##### usage: bacula_del_media_orphans [-h] [-d] [-dry]
bacula-del-media-orphans.py Delete all catalog entries, which backup volume
doesn't exist anymore. CONFIG: /etc/bacula-
scripts/bacula_del_media_orphans_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete jobs and storage files
  -dry        Simulate deletion


##### usage: bacula_del_purged_vols [-h] [-d] [-dry]
bacula-del-purged-vols.py Remove volumes and catalog entries for backups that
have been marked 'Purged' based on the deletion rules. Deletion rules: - Don't
delete full if there are unpurged (=dependent, =unpruned) incrementals or
diffs or less than four fulls. - Don't delete diff if there are dependent
incrementals or less than two diffs. - Don't delete incremental if there are
still dependent incrementals in the incremental chain. Latter should enforce
that incremental backups within a chain are deleted all at once. This script
will also work for remote storage daemons, provided that you setup the SSH
alias in /root/.ssh/config with the same hostname that you defined for the
"Address" (=hostname) in storages.conf. Why this script? We want to remove
purged backups for disk space, scaling reason, but we don't want to delete all
backups that have been marked as 'Purged', because if you don't do backups for
a very long time, and have set 'AutoPrune = yes', plus your Retention is due,
then important backups get deleted. Also if you delete a full backup, which
has been marked 'purged', but still have incremental backups dependent on it,
then you'll have a broken incremental backup chain. Developing notes: (1) We
have to get the jobname and backup time from the volume file with bls, because
purged volumes dont have any job entries in the catalog anymore. (2) Notice
that we use the clientname and filesetname to check a backup chain for
consistency, because the jobname doesn't distinctively display all backups of
a backup chain. Instead bacula uses all fileset and client name pairs. (3) Not
using paramiko in this script because we need `sudo` commands sometimes which
we allowed with %nopasswd% for the user. User notes: (1) We dont want to have
purged vols recycled/overwritten automatically. because it can happen that we
dont do a backup for a very long time and then we'd overwrite purged vols that
had old backups that would could still needed and leave us with no backups at
all. Instead our autorm script handles when to delete purged vols. => Make
sure to set `Recycle = No` in bacula configs. (2) After you changed Recycle to
'No' you may still have previous volumes marked with 'Recycle = Yes'. To make
all volumes in your database afterwards non recycable use this query in your
db backend: `UPDATE media SET recycle=0;` (3) Use `DRY_RUN = True` to simulate
this script. (4) If you use an external SD, make sure to setup SSH
accordingly. IMPORTANT! Notice that this script assumes your '~/.ssh/config'
uses the exact same FQDN as provided in the 'Address' directive of
/etc/bacula/bacula.dir.d/storages.conf for the SSH host alias. (5) For copy
jobs provide the unique 'mediatype' of the copy jobs storage, so that the
script won't use the 'JobLevel' from the parsed volume. We parse with the tool
`bls` and check if we find a hint of `bls` output in the 'PoolName' of the
JobLevel. This implies that you have to name your volumes with the appropriate
joblevel. That is e.g. "Full-Pool" or "my-full-pool" or "inc-copy-pool" or
"incremental-copy-pool". This workaround is required, because bacula writes
the wrong job level to the volume's metadata. In the catalog it's correct,
just not in the volume's metadata, where it always claims that the joblevel is
'I' for incremental. So our script's deletion algorithm wouldn't work,
therefore in that case we need to know the job level to decide if a volume
can't be deleted. (6) For remote storage daemons setup the ssh config like
this for example: Host phpc01e.ffm01. Hostname phpc01e.ffm01. Port 22
IdentityFile ~/.ssh/id_phpc01_ed25519 IdentitiesOnly yes User someuser
ConnectTimeout=5 Now also make sure that you add following commands for the
SSH user in sudoers with NOPASSWD or just SSH to root@your.host! someuser
ALL=NOPASSWD: /usr/bin/cat /etc/bareos/bareos-sd.conf someuser ALL=NOPASSWD:
/usr/bin/timeout 0.1 bls -jv * someuser ALL=NOPASSWD: /usr/bin/rm
/mnt/path/to/your/offsite/storage/* CONFIG: /etc/bacula-
scripts/bacula_del_purged_vols_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Remove purged jobs from catalog and disk
  -dry        Simulate deletion


##### usage: bacula_del_scatter.py [-h] [-d] [-dry]
bacula-del-jobs.py Delete redundant full media vols which are following to
narrowly. Example: F F F I F F F D F F F F F F F F x x x x x x x x We want a
full backup every 3 weeks, so we get a list of all consecutive Full backups
and make sure to mark the Full backups, that are allowed to be deleted. Only
Full backups, which have a Full following backup are allowed to be deleted.
Then apply the even spread function and have at maximum 1 Full backup within 3
weeks. The even spread function favors older backups. CONFIG: /etc/bacula-
scripts/bacula_prune_scattered_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -d          Delete redundant full media volumes
  -dry        Simulate deletion


##### usage: bacula_find_backups_bls [-h] [-f]
bacula_find_backups_bls.py Find the on-disk volume inside a backup directory
by parsing the volume information with `bls` to match a client or fileset.
CONFIG: /etc/bacula-scripts/bacula_find_backups_bls_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -f          Find disk volumes matching a client or fileset inside a backup
              directory


##### usage: bacula_prune_all [-h] [-p] [-dry]
bacula-prune-all.py Prune all existing volumes. Run `bconsole prune volume=x
yes` for all existing volumes. Latter command will only prune the volume, if
the configured retention time is passed. NO CONFIG

optional arguments:
  -h, --help  show this help message and exit
  -p          Prune all volumes
  -dry        Simulate deletion


##### usage: bacula_stats [-h] [-a] [-r] [--version]
bacula_stats 0.1.1 - Display recent and all backups.

optional arguments:
  -h, --help    show this help message and exit
  -a, --all     Return all backups.
  -r, --recent  Return recent backups
  --version     show program's version number and exit


##### usage: bacula_offsite_backup_age_watch [-h] [-c]
bacula-offsite-backup-age-watch.py Check when the last offsite backup was
performed and send a warning notification mail if the backup is too old. Add a
symlink to this script for example to cron.weekly. CONFIG: /etc/bacula-
scripts/bacula_offsite_backup_age_watch_conf.py

optional arguments:
  -h, --help  show this help message and exit
  -c          Check backup age


##### usage: bacula_add_client [-h] [-r] [-fd_fqdn FD_FQDN]
                         [-os_type {linux,windows}]
                         [-create_client_job CREATE_CLIENT_JOB]
                         [-create_client_copy_job CREATE_CLIENT_COPY_JOB]
                         [-dry_run]

bacula_add_client - Add a client with storage device to the bareos configs ***
Warning *** 1. Run this script only on the host of the bareos-director daemon,
because it needs to edit bareos-director config files. 2. Before adding a
client with this script, make sure you have configured Director resource in
`bareos-sd.d/director/bareos-dir.conf` and Storage resource in `bareos-
sd.d/storage/bareos-sd.conf` on your sd-daemon priorly, because you have to
type in the sd daemon password from `bareos-sd.d/director/bareos-dir.conf` and
the FQDN of the sd-daemon to this script's settings. 3. The script configures
on the client's fd-daemon the "Client resource" inside bareos-
fd.d/client/myself.conf with "client backup encryption" and creates the key
and cert needed for it. If you don't want to use client backup encryption
you'd have to alter the script to your needs, that is remove ssl key creation
and the config string. 4. Create the SSL master key and cert before running
this script That is: + mkdir -p /etc/bareos/certs + Create the SSL key
`openssl genrsa -aes256 -out /etc/bareos/certs/master.key -passout stdin 4096`
+ Create the public cert `openssl req -new -key master.key -x509 -out
/etc/bareos/certs/master.cert` - Don't merge key and cert. Only needed upon
restore and then the key needs the passphrase removed + Consider storing the
master key on a different secure location than on the bareos-dir. 5. Following
files can be written to: bareos-dir.d/client/bareos-fd.conf bareos-
dir.d/storage/File.conf bareos-sd.d/device/FileStorage.conf 6. Make sure all
passwords you enter to bareos resources are quoted 7. This script does not
configure storages. Do that manually

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

phserver01:root /usr/local/lib/python3.5/


---
#### Example for the offsite solution with the encfs script using dropbox:
- bacula_encfs_backup.py (requires you to setup a dropbox and encfs dir within the dropbox on the system where the
  director is, then the script automatically mounts and umounts before and after backup).
- Example job resource:

```
Job {
    Name = lt-phpc01lin-c01-phpc01lin
    Run Before Job = "bacula_encfs_backup_bacula mount %i"
    Run After Job = "bacula_encfs_backup_bacula umount"
    Run After Failed Job = "bacula_encfs_backup_bacula umount"
    Client  = phpc01lin-fd
    FileSet = phpc01lin-c01
    Jobdefs = lt
    Storage = sdropbox01
    Maximum Concurrent Jobs = 1
  }
  Device {
    Name = ddropbox01
    Media Type = fdropbox01
    Archive Device = /mnt/b01
    LabelMedia = yes;
    Random Access = yes;
    AutomaticMount = yes;
    RemovableMedia = no;
    AlwaysOpen = no;
    Maximum Concurrent Jobs = 20;
  }
```

- Make sure encfs encrypted and mount dir is owned by bacula, so if your encfs dir with the dropbox mount is in
  "/mnt/dropbox01/Dropbox/.encfs", run
    `chown -R bacula:bacula /mnt/dropbox01/`
  And for the mount directory e.g.:
    `chown -R bacula:bacula /mnt/c01`
- Create the dropbox dir for example in /mnt (not /root), because you need to have it in a traversable
  dir (chmod +x dir).
- Make sure to mount your encfs dir with `encfs-backup-bacula.py mount` manually before restoring.
- If you mount encfs by another user than bacula (e.g. root), then make sure to unmount it before
  doing backups, because bareos can't stat dirs mounted by another user, so this script will cancel the
  backup before it starts, when encfs is mounted by another user than bacula.
- It's recommended to store the encfs private key outside your encfs directory at another location to increase
  security.
  How to:
  1) First create an encfs6.xml by running the command normally in some directory. e.g.:
     encfs /tmp/encrypted /tmp/decrypted
  2) Copy /tmp/encrypted/.encfs6.xml (which contains the actual encryiption key within the <encodedKeyData> directive)
     to some secure location. E.g. copy it to /root/.encfs-keys/
  3) Create the actual encfs directory with e.g.:
     ENCFS6_CONFIG="/root/.encfs-keys/encfs6_dropbox01.xml" encfs /mnt/dropbox01/Dropbox/.c01 /mnt/b01/
  See this example config /etc/bacula-scripts/bacula_encfs_backups_conf.py:
```
     encfs_passphrase = "your_encfs_passphrase"
     encfs_dir = "/mnt/dropbox01/Dropbox/.c01"
     mount_dir = "/mnt/c01"
     # Here goes the .encfs6.xml file that we now store outside encfs
     os.environ["ENCFS6_CONFIG"] = "/root/.encfs-keys/encfs6_dropbox01.xml"
     cmd_mount = ["encfs", "--stdinpass", encfs_dir, mount_dir]
     cmd_password = ["echo", encfs_passphrase]
     cmd_umount = ["fusermount", "-u", mount_dir]
     cmd_lazy_umount = ["fusermount", "-z", "-u", mount_dir]
```

---
Project initially created in 05/2016
