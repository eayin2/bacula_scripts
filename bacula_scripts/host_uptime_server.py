""" host_uptime_server.py

Listen on a TCP socket for a host's uptime echo, packed into a json dumps. The json dumps
contains optionally a 'last_backup' json key with the seconds of the last performed backup
as its value.

Send an email notification, if the host's last uptime echo or performed backup is too long ago.

Open the configured TCP port in your firewall. E.g:
`iptables -A INPUT -p tcp --dport 11337 -j ACCEPT`
Provided you have `iptables-persistent` installed:
`iptables-save > /etc/iptables/rules.v4`

CONFIG /etc/bacula-scripts/host_uptime_conf.py
"""
import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict

from gymail.core import send_mail
from helputils.core import log

sys.path.append("/etc/bacula-scripts")
import host_uptime_server_conf as conf_mod


def CONF(attr):
    return getattr(conf_mod, attr, None)


class Host():
    
    def __init__(self):
        self.hosts = defaultdict(lambda: defaultdict(defaultdict))
        for host in CONF('HOST_LIST'):
            self.hosts[host]["notified"] = 0

    async def handle_echo(self, reader, writer):
        # If reading 1024 bytes is not enough or there are network issues,
        # read less bytes, like 512 bytes, and instead use a delimiter to
        # let the server know when the message is over.
        data = await reader.read(1024)
        msg = data.decode()
        msg = json.loads(msg)
        host_fqdn = msg.get("fqdn", None)
        last_backup = msg.get("last_backup", None)
        monitor_jobs = msg.get("monitor_jobs", None)

        if host_fqdn not in CONF('HOST_LIST'):
            writer.close()
        self.hosts[host_fqdn]["uptime"] = time.time()
        print(last_backup)
        self.hosts[host_fqdn]["last_backup"] = last_backup
        self.hosts[host_fqdn]["monitor_jobs"] = monitor_jobs
        writer.close()

    async def uptime_eval(self):    
        """Check uptime for all hosts"""
        while True:
            await asyncio.sleep(1)
            for host, data in self.hosts.items():
                now = time.time()
                if not data["notified"]:
                    data["notified"] = CONF('DELAY_NOTIFY') + 1
                if not data["uptime"]:
                    data["uptime"] = CONF('DOWNTIME') + 1 + now
                if now - data["notified"] > CONF('DELAY_NOTIFY'):
                    if now - data["uptime"] > CONF('DOWNTIME'):
                        msg = "%s hasn't responded since %s seconds" % (host, CONF('DOWNTIME'))
                        log.error(msg)
                        send_mail("error", "Host %s is down" % host, msg)
                        data["notified"] = time.time()
                    if data["last_backup"]:
                        if data["last_backup"] > CONF('LAST_BACKUP_MAX_DAYS'): ## * (24*60*60):
                            msg = "Last backup is older than %s days for director host %s." % (
                                CONF('LAST_BACKUP_MAX_DAYS'), host
                            )
                            log.error(msg)
                            send_mail("error", "Backup too old for host %s" % host, msg)
                            data["notified"] = time.time()
                    if data["monitor_jobs"]:
                        for job_name, job_last_backup in data["monitor_jobs"].items():
                            if job_last_backup > CONF('LAST_BACKUP_MAX_DAYS'): ## * (24*60*60):
                                msg = """\
The backup job %s is older than %s days for the director host %s.\
""" % (job_name, CONF('LAST_BACKUP_MAX_DAYS'), host)
                                log.error(msg)
                                send_mail("error", "Backup too old for host %s" % host, msg)
                                data["notified"] = time.time()

    def run(self):
        loop = asyncio.get_event_loop()
        coro = asyncio.start_server(self.handle_echo, CONF('LISTEN_IP'), CONF('LISTEN_PORT'), loop=loop)
        server = loop.run_until_complete(coro)
        asyncio.ensure_future(self.uptime_eval())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-r", action="store_true", help="Run host_uptime server")
    args = p.parse_args()
    if args.r:
        h = Host()
        h.run()


if __name__ == "__main__":
    main()
