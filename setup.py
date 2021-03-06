import re
from distutils.core import setup
from setuptools import find_packages

VERSIONFILE="bacula_scripts/_version.py"
verstrline = open(VERSIONFILE, "rt").read()
VSRE = r"^__version__ = ['\"]([^'\"]*)['\"]"
mo = re.search(VSRE, verstrline, re.M)
if mo:
    verstr = mo.group(1)
else:
    raise RuntimeError("Unable to find version string in %s." % (VERSIONFILE,))

setup(
    name="bacula_scripts",
    version=verstr,
    author="eayin2",
    author_email="eayin2@gmail.com",
    packages=find_packages(),
    url="https://github.com/eayin2/bacula_scripts",
    description="Bunch of bacula scripts. Includes also scripts to realize offsite backup solution.",
    install_requires=[
        "gymail",
        "helputils",
        "psycopg2-binary",
        "pexpect",
        "lark-parser"],
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "bacula_add_client = bacula_scripts.bacula_add_client:main",
            "bacula_db_backup = bacula_scripts.bacula_db_backup:main",
            "bacula_del_catalog_jobids = bacula_scripts.bacula_del_catalog_jobids:main",
            "bacula_del_failed_jobs_and_volume = bacula_scripts.bacula_del_failed_jobs_and_volume:main",
            "bacula_del_jobs = bacula_scripts.bacula_del_jobs:main",
            "bacula_del_media_orphans = bacula_scripts.bacula_del_media_orphans:main",
            "bacula_del_purged_vols = bacula_scripts.bacula_del_purged_vols:main",
            "bacula_del_scatter.py = bacula_scripts.bacula_del_scatter:main",
            "bacula_del_vols_missing_catalog = bacula_scripts.bacula_del_vols_missing_catalog:main",
            "bacula_encfs_backup = bacula_scripts.bacula_encfs_backup:main",
            "bacula_find_backups_bls = bacula_scripts.bacula_find_backups_bls:main",
            "bacula_monitor = bacula_scripts.bacula_monitor:main",
            "bacula_offsite_backup_age_watch = bacula_scripts.bacula_offsite_backup_age_watch:main",
            "bacula_prune_all = bacula_scripts.bacula_prune_all:main",
            "disk_full_notifier = bacula_scripts.disk_full_notifier:main",
            "host_uptime_server = bacula_scripts.host_uptime_server:main",
            "host_uptime_client = bacula_scripts.host_uptime_client:main",
        ],
    },
)
