""" host_uptime_client.py

Connect to the host_uptime server and send a json dictionary to the echo server containing this
hosts FQDN and the date of the latest performed bacula backup.

CONFIG: /etc/bacula-scripts/host_uptime_client_conf.py
"""

# MONITOR_FQDN: FQDN of the host_uptime server, which this hosts uptime is sent to
MONITOR_FQDN = "phpc01.ffm01."
MONITOR_PORT = 11337
# DIRECTOR_FQDN: FQDN of this client. This client should be the same host where the bacula
#   director is running
DIRECTOR_FQDN = "phserver01.ffm01."
