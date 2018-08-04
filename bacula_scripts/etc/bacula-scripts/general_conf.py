""" general_conf.py

System and database credential configurations for the bacula_scripts package.
"""

user = "bareos"
group = "bareos"
sd_conf, storages_conf = ("/etc/bareos/bareos-sd.conf", "/etc/bareos/bareos-dir.d/storages.conf")
# Leave the db_password empty if you don't need one. psycopg2 won't bother an empty password kwarg.
db_host, db_user, db_name, db_password = ("phserver01", "bareos", "bareos", "")
services = ["bareos-dir", "postgresql"]
