#!/usr/bin/python3
# -*- coding: utf-8-*-
""" host_uptime_client.py

Connect to the host_uptime server and send a json dictionary to the echo server containing this
hosts FQDN and the date of the latest performed bacula backup.

CONFIG: /etc/bacula-scripts/host_uptime_client_conf.py
"""
import argparse
import asyncio
import datetime
import json
import os
import psycopg2
import re
import sys
from argparse import RawDescriptionHelpFormatter
from subprocess import Popen, PIPE

from helputils.core import format_exception, liget, log, systemd_services_up

sys.path.append("/etc/bacula-scripts")
import host_uptime_client_conf as conf_mod
from general_conf import db_host, db_user, db_name, db_password, services


def CONF(attr):
    return getattr(conf_mod, attr, None)


# Get realendtime of latest backup
SQL_SUCCESSFUL_JOBS = """
SELECT j.realendtime
FROM job j
WHERE j.jobstatus IN ('T', 'W')
AND j.level IN ('F', 'I', 'D')
AND j.type IN ('B', 'C')
"""

SQL_ORDER_BY = "ORDER BY j.realendtime DESC LIMIT 1"


async def tcp_echo_client(message, loop):
    fut =  asyncio.open_connection(
        CONF('MONITOR_FQDN'), CONF('MONITOR_PORT'), loop=loop
    )

    try:
        reader, writer = await asyncio.wait_for(fut, timeout=3)
    except asyncio.TimeoutError:
        print("Timed out")
        return
    writer.write(message.encode())
    data = await reader.read(100)
    print('Received: %r' % data.decode())
    print('Close the socket')
    writer.close()


def last_backup(job_name=None):
    if job_name:
        sql_job_name = " AND j.name='%s'" % job_name
        SQL = "%s %s %s" % (SQL_SUCCESSFUL_JOBS, sql_job_name, SQL_ORDER_BY)
    else:
        SQL = "%s %s" % (SQL_SUCCESSFUL_JOBS, SQL_ORDER_BY)
    try:
        con = psycopg2.connect(
            database=db_name,
            user=db_user,
            host=db_host,
            password=db_password
        )
        cur = con.cursor()
        cur.execute(SQL)
        volnames = cur.fetchall()
    except Exception as e:
        log.error(format_exception(e))
    realendtime = liget(liget(volnames, 0), 0)
    print(realendtime)
    if not realendtime:
        log.error("realendtime is None")
        return None
    last_backup = (datetime.datetime.now() - realendtime).total_seconds()
    return last_backup


def run():
    systemd_services_up(services)
    jobs = CONF("MONITOR_JOBS")
    monitor_jobs = None
    if jobs:
        monitor_jobs = dict()
        for job_name in jobs:
            monitor_jobs[job_name] = last_backup(job_name)
    data = {
        "fqdn": CONF('DIRECTOR_FQDN'),
        "last_backup": last_backup(),
        "monitor_jobs": monitor_jobs,
    }
    print(data)
    message = json.dumps(data)
    print(message)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(tcp_echo_client(message, loop))
    loop.close()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    p.add_argument("-r", action="store_true", help="Run host_uptime client")
    args = p.parse_args()
    if args.r:
        run()


if __name__ == "__main__":
    main()
