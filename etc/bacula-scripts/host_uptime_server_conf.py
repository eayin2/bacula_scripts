""" host_uptime_server.py

Listen on a TCP socket for a host's uptime echo, packed into a json dumps. The json dumps
contains optionally a 'last_backup' json key with the seconds of the last performed backup
as its value.

Send an email notification, if the host's last uptime echo or performed backup is too long ago.

CONFIG /etc/bacula-scripts/host_uptime_conf.py
"""

# LISTEN_IP: Subnet to listen to. 127.0.0.1 means only the local computer can connect to the
#   socket. 0.0.0.0 means any host can connect. 192.168.2.0 means the subnet 192.168.2.0/24 can
#   connect to the socket.
LISTEN_IP = "0.0.0.0"
LISTEN_PORT = "11337"
# HOST_LIST: List of hosts to evaluate the downtime of
HOST_LIST = [
    "phserver01.ffm01.",
    "phpc01.ffm01.",
    "bareos01.ffm01.",
]
# DELAY_NOTIFY: Delay between host downtime notifications
DELAY_NOTIFY = 60 * 60 * 24 * 4
# DOWNTIME: Time after a host is considered down and an email is sent out
DOWNTIME = 60 * 60 * 24 * 4
# LAST_BACKUP_MAX_DAYS: Maximum tolerated age of the latest backup
LAST_BACKUP_MAX_DAYS = 5
