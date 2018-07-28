#!/usr/bin/python3
# -*- coding: utf-8 -*-
""" bacula-del-purged-vols.py

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
(1) We have to get the jobname and backup time from the volume file with bls, because purged volumes dont have any job
    entries in the catalog anymore.
(2) Notice that we use the clientname and filesetname to check a backup chain for consistency, because the jobname
    doesn't distinctively display all backups of a backup chain. Instead bacula uses all fileset and client name
    pairs.
(3) Not using paramiko in this script because we need `sudo` commands sometimes which we allowed with %nopasswd% for the
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
    Now also make sure that you add following commands for the SSH user in sudoers with
    NOPASSWD or just SSH to root@your.host!
      someuser ALL=NOPASSWD: /usr/bin/cat /etc/bareos/bareos-sd.conf
      someuser ALL=NOPASSWD: /usr/bin/timeout 0.1 bls -jv *
      someuser ALL=NOPASSWD: /usr/bin/rm /mnt/path/to/your/offsite/storage/*

CONFIG: /etc/bacula-scripts/bacula_del_purged_vols_conf.py
"""
import argparse
import os
import re
import sys
import time
import traceback
import socket
from argparse import RawDescriptionHelpFormatter
from datetime import datetime
from subprocess import Popen, PIPE

import psycopg2
from helputils.core import (format_exception, islocal, _isfile, find_mountpoint, remote_file_content,
                            systemd_services_up, setlocals)
from helputils.defaultlog import log
sys.path.append("/etc/bacula-scripts")
import bacula_del_purged_vols_conf as conf_mod
from bacula_scripts.bacula_parser import bacula_parse
from general_conf import sd_conf, storages_conf, db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


def CONF_SET(attr, val):
    return setattr(conf_mod, attr, val)


def parse_vol(volume, hn=False):
    """Parses volume with bls and returns jobname and timestamp of job. Make sure to have bls in your $PATH and add
       `user ALL=NOPASSWD: /usr/bin/timeout 0.1 bls -jv` to sudoers"""
    log.debug("Run `/usr/bin/timeout 0.1 bls -jv %s` (should be absolute path)" % volume)
    cmd = ["/usr/bin/timeout", "0.1", "bls", "-jv", volume]
    if hn and not islocal(hn):
        cmd = ["ssh", hn, "sudo"] + cmd
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    out = str(out)
    vol = os.path.basename(volume)
    try:
        cn = re.search("\\\\nClientName\s+:\s(.*?)\\\\n", out).group(1)
        fn = re.search("\\\\nFileSet\s+:\s(.*?)\\\\n", out).group(1)
        jl = re.search("\\\\nJobLevel\s+:\s(.*?)\\\\n", out).group(1)
        ti = re.search("\\\\nDate written\s+:\s(.*?)\\\\n", out).group(1)
        jn = re.search("\\\\nJobName\s+:\s(.*?)\\\\n", out).group(1)
        mt = re.search("\\\\nMediaType\s+:\s(.*?)\\\\n", out).group(1)
        pn = re.search("\\\\nPoolName\s+:\s(.*?)\\\\n", out).group(1)
    except:
        log.info("Deleting volume, because no metadata found: %s " % vol)
        return None
    log.info("cn:{0}, fn:{1}, jl:{2}, ti:{3}, mt:{4}, vol:{5}, jn:{6}, pn:{7}".format(cn, fn, jl, ti, mt, vol, jn, pn))
    try:
        ti = ti.replace("\\xc3\\xa4", "ä")  # Temp fix for backups that were made while my locals where broken
        dt = datetime.strptime(ti, "%d-%b-%Y %H:%M")
    except:
        setlocals()
        dt = datetime.strptime(ti, "%d-%b-%Y %H:%M")
    ts = time.mktime(dt.timetuple())
    return (cn, fn, ts, jl, jn, mt, pn)


def build_volpath(volname, storagename, sd_conf_parsed, storages_conf_parsed, hn=False):
    """Looks in config files for device path and returns devicename joined with the volname."""
    for storage_name, storage_value in storages_conf_parsed["Storage"].items():
        if storagename == storage_name:
            devicename = storage_value["Device"]
            for device_name, device_value in sd_conf_parsed["Device"].items():
                if devicename == device_name:
                    print(device_value)
                    volpath = os.path.join(device_value["ArchiveDevice"], volname)
                    # log.info("volpath %s: devicename in sd_conf and storages_conf matched: %s" % (volpath,
                    #           devicename))
                    if not find_mountpoint(device_value["ArchiveDevice"], hn) == "/":
                        return volpath


def storagehostname(storages_conf_parsed, sn):
    """Parses stoarges.conf for storagename and returns address of storage"""
    for storage_name, storage_value in storages_conf_parsed["Storage"].items():
        if sn == storage_name:
            return storage_value["Address"]


def del_backups(remove_backup):
    """Deletes list of backups from disk and catalog.

    Make sure to add to your sudoers file something like:
    `user ALL=NOPASSWD: /usr/bin/rm /mnt/8tb01/offsite01/*`. Notice that I added the offsite's path with the
    wildcard after the rm command, so that the user can only use rm for that directory.
    """
    for volpath, hn in remove_backup:
        volname = os.path.basename(volpath)
        log.info("Deleting %s:%s" % (hn, volpath))
        if not CONF('DRY_RUN'):
            if islocal(hn):
                try:
                    os.remove(volpath)
                    log.info("Deleted %s" % volpath)
                except Exception as e:
                    log.error(format_exception(e))
                    log.info("Deleting failed, apparently volpath %s doesn't exist." % volpath)
            elif not islocal(hn):
                try:
                    p = Popen(["ssh", hn, "sudo", "/usr/bin/rm", volpath])
                    o, e = p.communicate()
                    if e:
                        if "ssh: Could not resolve hostname" in e.decode("UTF-8"):
                            log.error(e)
                            log.error("Please setup ssh keys for the storage host, so that this script can ssh to the "
                                      "host %s" % hn)
                            continue
                except Exception as e:
                    log.error(format_exception(e))
                    log.info("Deleting failed, apparently volpath %s doesn't exist (remote delete)." % volpath)
            p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
            p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            log.debug("out: %s, err: %s" % (out, err))


def run(dry_run=False):
    CONF_SET('DRY_RUN', dry_run)
    systemd_services_up(services)
    try:
        con = psycopg2.connect(database=db_name, user=db_user, host=db_host, password=db_password)
        cur = con.cursor()
        cur.execute("SELECT distinct m.volumename, s.name, m.volstatus, j.jobtdate, j.filesetid, j.clientid, j.level, "
                    "c.name, f.fileset, j.name, mt.mediatype "
                    "FROM media m, storage s, job j, jobmedia jm, fileset f, client c, mediatype mt "
                    "WHERE m.storageid=s.storageid "
                    "AND jm.mediaid=m.mediaid "
                    "AND jm.jobid=j.jobid "
                    "AND f.filesetid=j.filesetid "
                    "AND j.clientid=c.clientid "
                    "AND mt.mediatype=m.mediatype;")
        volumes = cur.fetchall()
        cur.execute("SELECT distinct m.volumename, s.name "
                    "FROM media m, storage s "
                    "WHERE m.storageid=s.storageid "
                    "AND m.volstatus='Purged';")
        purged_vols = cur.fetchall()
    except Exception as e:
        log.error(format_exception(e))
    unpurged_backups = [x for x in volumes if x[2] != "Purged"]
    full_purged, diff_purged, inc_purged, remove_backup = [list() for x in range(4)]

    sd_conf_parsed = bacula_parse("bareos-sd")
    storages_conf_parsed = bacula_parse("bareos-dir")

    log.info("\n\n\n\nSorting purged volumes to full_purged, diff_purged and inc_purged.\n\n")
    log.info("There are %s purged_vols and %s unpurged_backups" % (len(purged_vols), len(unpurged_backups)))
    for volname, storagename in purged_vols:
        hn = storagehostname(storages_conf_parsed, storagename)
        if islocal(hn):
            volpath = build_volpath(volname, storagename, sd_conf_parsed, storages_conf_parsed)
        elif not islocal(hn):
            log.info("content of %s:%s (hn:filename)" % (hn, fn))
            remote_sd_conf_parsed = bacula_parse("bareos-sd", hn=hn)
            volpath = build_volpath(volname, storagename, remote_sd_conf_parsed, storages_conf_parsed, hn)
        if not volpath:
            log.info("Skipping this purged volume, because storage device is not mounted. %s:%s" % (hn, volpath))
            continue
        elif _isfile(volpath, hn) == False and volpath:
            log.info("Deleting backup from catalog, because volume doesn't exist anymore: %s:%s" % (hn, volpath))
            del_backups([(volpath, hn)])
            continue
        elif _isfile(volpath, hn):
            vol_parsed = parse_vol(volpath, hn)
            if vol_parsed:
                cn, fn, ts, jl, jn, mt, pn = vol_parsed
            else:
                if CONF('DEL_VOLS_WITH_NO_METADATA'):
                    log.info("Removing volume, because it has no metadata. Removing both file and catalog record.")
                    os.remove(volpath)
                    p1 = Popen(["echo", "delete volume=%s yes" % volname], stdout=PIPE)
                    p2 = Popen(["bconsole"], stdin=p1.stdout, stdout=PIPE)
                    p1.stdout.close()
                    out, err = p2.communicate()
                    log.debug("out: %s, err: %s" % (out, err))
                continue
        else:
            continue
        x1 = (volpath, cn, fn, ts, hn, jn, mt)
        # Workaround for copy volumes, which don't store the right job level. Notice
        #  this works only if your pool names include the job level (e.g. full, inc or diff)
        if mt in CONF('OFFSITE_MT'):
            pnl = pn.lower()
            if "full" in pnl:
                jl = "F"
            elif "diff" in pnl:
                jl = "D"
            elif "inc" in pnl:
                jl = "I"
        full_purged.append(x1) if jl == "F" else ""
        diff_purged.append(x1) if jl == "D" else ""
        inc_purged.append(x1) if jl == "I" else ""
    log.info("\n\n\n")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("\n\n\nDeciding which purged full vols to delete")
    for volpath, cn, fn, backup_time, hn, jn, mt in full_purged:
        # log.debug("\n\nDeciding which purged full vols to delete: cn: {0}, fn: {1}, backup_time: {2}, volpath:
        #            {3}".format(cn, fn, backup_time, volpath))
        newer_full_backups = [x3 for x3 in unpurged_backups if x3[6] == "F" and x3[3] > backup_time and cn == x3[7] and
                              fn == x3[8] and jn == x3[9] and mt == x3[10]]
        if len(newer_full_backups) == 0:
            log.info("Skipping and not removing {0}, because it's the newest full backup.".format(volpath))
            continue
        next_full_backup = min(newer_full_backups, key=lambda x: x[3])
        newer_full_diff_backups = [x3 for x3 in unpurged_backups if x3[6] in ["F", "D"] and x3[3] > backup_time and
                                   cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        next_full_diff_backup = min(newer_full_diff_backups, key=lambda x: x[3])
        inc_backups = [x3 for x3 in unpurged_backups if x3[6] == "I" and x3[3] > backup_time and x3[3] <
                       next_full_diff_backup[3] and cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        # here we use next_full_backup
        diff_backups = [x3 for x3 in unpurged_backups if x3[6] == "D" and x3[3] > backup_time and x3[3] <
                        next_full_backup[3] and cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        full_backups = [x3 for x3 in unpurged_backups if x3[6] == "F" and cn == x3[7] and fn == x3[8] and
                        jn == x3[9] and mt == x3[10]]
        # log.info("newer_full_backups %s" % str(newer_full_backups))
        # log.info("newer_full_diff_backups %s" % str(newer_full_diff_backups))
        # log.info("next_full_diff_backup %s" % str(next_full_diff_backup))
        # log.info("inc_backups %s" % inc_backups)
        if len(inc_backups) > 0:
            log.info("Not removing {0}, because there are still incremental backups dependent on it.".format(volpath))
        elif len(diff_backups) > 0:
            log.info("Not removing {0}, because there are still diff backups dependent on it.".format(volpath))
            continue
        elif len(full_backups) < 3:
            log.info("Not removing {0}, because we have less than four three backups in total.".format(volpath))
            continue
        else:
            log.info("Adding backup to remove list")
            remove_backup.append((volpath, hn))
    log.info("\n\n\n")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("\n\n\nDeciding which purged incremental vols to delete")
    for volpath, cn, fn, backup_time, hn, jn, mt in inc_purged:
        newer_full_diff_backups = [x3 for x3 in unpurged_backups if x3[6] in ["F", "D"] and x3[3] > backup_time and
                                   cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        older_full_diff_backups = [x3 for x3 in unpurged_backups if x3[6] in ["F", "D"] and x3[3] < backup_time and
                                   cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        inc_backups = list()
        for x3 in unpurged_backups:
            inc_filter = [x3[6] == "I", cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
            if newer_full_diff_backups:
                next_full_backup = min(newer_full_diff_backups, key=lambda x: x[3])
                inc_filter.append(x3[3] < next_full_backup[3])
            if older_full_diff_backups:
                prev_full_backup = max(older_full_diff_backups, key=lambda x: x[3])
                inc_filter.append(x3[3] > prev_full_backup[3])
            if all(inc_filter):
                inc_backups.append(x3)
        if len(inc_backups) > 0:
            log.info("Not removing {0}, because there are still chained inc backups that are not "
                     "purged.".format(volpath))
            continue
        else:
            log.info("Adding backup to remove list")
            remove_backup.append((volpath, hn))
    log.info("\n\n\n")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~~*~*~*~~~~~*~*~*~")
    log.info("\n\n\nDeciding which purged diff vols to delete")
    for volpath, cn, fn, backup_time, hn, jn, mt in diff_purged:
        newer_full_or_diff_backups = [x3 for x3 in unpurged_backups if x3[6] in ["F", "D"] and x3[3] > backup_time and
                                      cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
        if newer_full_or_diff_backups:
            next_full_or_diff_backup = min(newer_full_or_diff_backups, key=lambda x: x[3])
            inc_backups = [x3 for x3 in unpurged_backups if x3[6] == "I" and x3[3] > backup_time and x3[3] <
                           next_full_or_diff_backup[3] and cn == x3[7] and fn == x3[8] and jn == x3[9] and mt == x3[10]]
            diff_backups = [x3 for x3 in unpurged_backups if x3[6] == "D" and cn == x3[7] and fn == x3[8] and jn ==
                            x3[9] and mt == x3[10]]
            # log.info("newer_full_or_diff_backups %s" % str(newer_full_or_diff_backups))
            # log.info("next_full_or_diff_backup %s" % str(next_full_or_diff_backup))
            # log.info("inc_backups %s" % inc_backups)
            if len(inc_backups) > 0:
                log.info("Not removing {0}, because there are still incremental backups dependent on "
                         "it.".format(volpath))
                continue
            elif len(diff_backups) < 2:
                log.info("Not removing {0}, because we have less than four full backups in total.".format(volpath))
                continue
            else:
                log.info("Adding backup to remove list")
                remove_backup.append((volpath, hn))
    log.info("\n\n\n\nDecisions made. Initating deletion.")
    log.info("remove_backup list: %s" % remove_backup)
    if len(remove_backup) == 0:
        log.info("Nothing to delete")
    del_backups(remove_backup)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-d", action="store_true", help="Remove purged jobs from catalog and disk")
    p.add_argument("-dry", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.d and args.dry:
        run(dry_run=True)
    elif args.d and not args.dry:
        run(dry_run=False)
