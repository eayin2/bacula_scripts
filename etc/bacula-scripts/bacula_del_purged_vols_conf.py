"""
bacula-del-purged-vols.py

Description:
Removing volumes and catalog entries for backups that have been marked 'Purged' based on deletion rules. Script's
deletion rules are:
- Don't delete full if there are unpurged (=dependent, =unpruned) incrementals or diffs or less than four fulls.
- Don't delete diff if there are dependent incrementals or less than two diffs.
- Don't delete incremental if there are still dependent incrementals in the incremental chain.
Latter should enforce that incremental backups witihn a chain are deleted all at once.
This script will also work for remote storage daemons, provided that you setup the ssh alias in /root/.ssh/config
with the same hostname that you defined for the "Address" (=hostname) in storages.conf.

Why this script?:
We want to remove purged backups for disk space (scaling reason), but we don't want to delete all
backups that have been marked as 'Purged', because if you don't do backups for a very long time, but you have
AutoPrune = yes and your Retention is due then you'll lose backups. Also if you delete a full backup (which was marked
as purged) but still have incremental backups dependent on it, you'll have a broken incremental backup chain.

Dev notes:
(1) We have to get the jobname and backup time from the volume file with bls, because purged volumes dont have any job
    entries in the catalog anymore.
(2) Notice that we use the clientname and filesetname to check a backup chain for consistency, because the jobname
    doesn't distinctively display all backups of a backup chain. Instead bacula uses all fileset and client name
    pairs.
(3) Not using paramiko in this script because we need `sudo` commands sometimes which we allowed with %nopasswd% for the user

User notes:
(1) We dont want to have purged vols recycled/overwritten automatically. because it can happen that we dont do a
    backup for a very long time and then we'd overwrite purged vols that had old backups that would could still needed
    and leave us with no backups at all. Instead our autorm script handles when to delete purged vols.
    => So make sure that `Recycle = No` is set in bacula configs.
(2) After you changed Recycle to 'No' you may still have previous volumes marked with Recycle = Yes. To
    make all volumes in your database afterwards non recycable use this query in your db backend:
    UPDATE media SET recycle=0;
(3) Use `dry_run = True` to test this script.
(4) If you use an external sd, make sure to setup ssh for it accordingly. IMPORTANT: Notice that this script assumes
    that your ~/.ssh/config uses the exact same hostname as provided to Address in /etc/bacula/bacula.dir.d/storages.conf
    for the ssh host alias.
(5) For copy jobs you have to provide the unique mediatype of the copy jobs storage, then the script will not use the
    JobLevel from the parsed volume (we parse with the tool bls), but instead checks if it finds in the PoolName (also
    from the bls output) a hint of what JobLevel the volume is. So this implies that you have to name your volumes
    with the appropriate joblevel. E.g. "Full-Pool" or "my-full-pool" or "inc-copy-pool" or "incremental-copy-pool".
    This workaround has to be done, because bacula writes the wrong job level to the volume's metadata (in the catalog
    it's correct, just not in the volume's metadata, where it always claims that the joblevel is 'I' for incremental),
    but then our script's deletion algorithm won't work, so we need to know the job level to decide if a volume can't
    be deleted.
(6) For remote storage daemons setup the ssh config like this for example:
        Host phpc01e.ffm01.
        Hostname phpc01e.ffm01.
        Port 22
        IdentityFile ~/.ssh/id_phpc01_ed25519
        IdentitiesOnly yes
        User someuser
        ConnectTimeout=5
    Now also make sure that you add following commands for the ssh user in sudoers with NOPASSWD:
        someuser ALL=NOPASSWD: /usr/bin/cat /etc/bareos/bareos-sd.conf
        someuser ALL=NOPASSWD: /usr/bin/timeout 0.04 bls -jv *
        someuser ALL=NOPASSWD: /usr/bin/rm /mnt/path/to/your/offsite/storage/*
"""
# Config:
# Put in here your storage's mediatype
offsite_mt = ("foffsite01")  # Workaround, see User notes (5)

dry_run = False
#dry_run = True
