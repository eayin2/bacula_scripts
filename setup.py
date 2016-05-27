from distutils.core import setup
from setuptools import find_packages

setup(
    name="bacula_scripts",
    version="0.1.3",
    author="eayin2",
    author_email="eayin2 at gmail dot com",
    packages=find_packages(),
    url="https://github.com/eayin2/bacula_scripts",
    description="Bunch of bacula scripts. Includes also scripts to realize offsite backup solution.",
    install_requires=["gymail", "helputils", "psycopg2"],
    entry_points={
        'console_scripts': [
            'bacula_del_jobs = bacula_scripts.bacula_del_jobs',
            'bacula_del_media_orphans = bacula_scripts.bacula_del_media_orphans',
            'bacula_del_failed_jobs = bacula_scripts.bacula_del_failed_jobs.py',
            'bacula_offsite_backup_age_watch = bacula_scripts.bacula_offsite_backup_age_watch',
            'bacula_offsite_clean_and_umount = bacula_scripts.bacula_offsite_clean_and_umount',
            'bacula_find_backups_bls = bacula_scripts.bacula_find_backups_bls',
            'bacula_del_purged_vols = bacula_scripts.bacula_del_purged_vols',
            'bacula_del_catalog_jobids = bacula_scripts.bacula_del_catalog_jobids',
        ],
    },
)
