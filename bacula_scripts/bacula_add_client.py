# -*- coding: utf-8 -*-
"""bacula_add_client - Add a client with storage device to the bareos configs

*** Warning ***
1. Run this script only on the host of the bareos-director daemon, because it needs
   to edit bareos-director config files.
2. Before adding a client with this script, make sure you have configured
   Director resource in `bareos-sd.d/director/bareos-dir.conf` and
   Storage resource in `bareos-sd.d/storage/bareos-sd.conf`
   on your sd-daemon priorly, because you have to type in the sd daemon password
   from `bareos-sd.d/director/bareos-dir.conf` and the FQDN of the sd-daemon to
   this script's settings.
3. The script configures on the client's fd-daemon the "Client resource" inside
   bareos-fd.d/client/myself.conf with "client backup encryption" and creates
   the key and cert needed for it. If you don't want to use client backup encryption
   you'd have to alter the script to your needs, that is remove ssl key creation
   and the config string.
4. Create the SSL master key and cert before running this script
   That is:
   + mkdir -p /etc/bareos/certs
   + Create the SSL key
     `openssl genrsa -aes256 -out /etc/bareos/certs/master.key -passout stdin 4096`
   + Create the public cert
     `openssl req -new -key master.key -x509 -out /etc/bareos/certs/master.cert`
   - Don't merge key and cert. Only needed upon restore and then the key needs the
     passphrase removed
   + Consider storing the master key on a different secure location than on the
     bareos-dir.
5. Following files can be written to:
   bareos-dir.d/client/bareos-fd.conf
   bareos-dir.d/storage/File.conf
   bareos-sd.d/device/FileStorage.conf
6. Make sure all passwords you enter to bareos resources are quoted
7. This script does not configure storages. Do that manually
"""
import argparse
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.append("/etc/bacula-scripts")
import bacula_add_client_conf as conf_mod
from bacula_scripts.bacula_parser import bacula_parse


def CONF(attr):
    return getattr(conf_mod, attr, None)


def CONF_SET(attr, val):
    return setattr(conf_mod, attr, val)


class AddClient():

    def __init__(self):
        self.client_exists = False

    def user_input(self):
        if not self.fd_fqdn:
            self.fd_fqdn = input("Enter the client's FQDN you want to add to bareos config: ")
        if not self.os_type:
            while True:
                self.os_type = input("OS Type, enter 'linux' or 'windows': ")
                if self.os_type.lower() in ["linux", "windows"]:
                    break
                print("Only 'linux' and 'windows' accepted as choices.")
        if not self.create_client_job:
            create_client_job = input("Do you want to create a job for this client? Enter (y/N): ")
            if create_client_job == "" or create_client_job.lower() in ("n", "no"):
                self.create_client_job = False
            elif create_client_job.lower() in ("y", "yes"):
                self.create_client_job = True
        if not self.create_client_copy_job:
            create_client_copy_job = input("Do you want to create a *copy* job for this client? Enter (y/N): ")
            if create_client_copy_job == "" or create_client_copy_job.lower() in ("n", "no"):
                self.create_client_copy_job = False
            elif create_client_copy_job.lower() in ("y", "yes"):
                self.create_client_copy_job = True

    def write_client_resource(self):
        """Add client to resource. Return None if client exists in the config.
        # Create configuration files in bareos.dir.d/ on bareos-director host
        """
        client_conf = self.dir_conf.get('Client')
        if client_conf:
            if client_conf.get("%s-fd" % self.fd_fqdn, None):
                print("Client exists already")
                self.client_exists = True
                return None
        if not self.dry_run:
            with open(CONF('CLIENT_DIR_CONF'), "a", encoding='utf8') as f:
                f.write("""\n
Client {{
  Name = {0}-fd
  Address = {0}
  Password = '{1}'
  File Retention = 14 months
  Job Retention = 14 months
}}""".format(self.fd_fqdn, self.fd_password))
        return True

    def write_job(self):
        job_conf = self.dir_conf.get('Job')
        job_name = "%s-%s-%s" % (CONF('ADD_JOB_JOBDEFS'), CONF('ADD_JOB_FILESET'), self.fd_fqdn)
        if job_conf:
            if job_conf.get(job_name, None):
                print("Job exists already")
                return None
        if not self.dry_run:
            with open(CONF('JOB_DIR_CONF'), "a", encoding='utf8') as f:
                f.write("""\n
Job {
  Name    = %s
  Client  = "%s-fd"
  FileSet = %s
  Jobdefs = %s
  Storage = %s
}""" % (
    job_name,
    self.fd_fqdn, 
    CONF('ADD_JOB_FILESET'),
    CONF('ADD_JOB_JOBDEFS'),
    CONF('ADD_JOB_STORAGE')
    )
)
        print("""\
Written following configuration files:\n%s\n\n..Done
""" % CONF('JOB_DIR_CONF')
    )

    def write_copy_job(self):
        job_conf = self.dir_conf.get('Job')
        job_name = "%s-%s-%s" % (CONF('ADD_JOB_JOBDEFS'), CONF('ADD_JOB_FILESET'), self.fd_fqdn)
        copy_job_name = "copy-%s-%s-%s" % (CONF('ADD_COPY_JOB_JOBDEFS'), CONF('ADD_JOB_FILESET'), self.fd_fqdn)
        if job_conf:
            if job_conf.get(copy_job_name, None):
                print("Copy job %s exists already" % copy_job_name)
                return None
        if not self.dry_run:
            with open(CONF('COPY_JOB_DIR_CONF'), "a", encoding='utf8') as f:
                f.write("""\n
Job {{
  Name = {0}
  Pool = {1}
  Client  = "{2}-fd"
  Jobdefs = {3}
  Storage = "{4}"
  Maximum Concurrent Jobs = 4
  Selection Type = "SQLQuery"
  Selection Pattern = "
SELECT j0.jobid, j0.starttime
FROM (
  SELECT DISTINCT j1.jobid, j1.starttime
  FROM job j1, pool p1
  WHERE p1.name='{1}'
  AND p1.poolid=j1.poolid
  AND j1.type = 'B'
  AND j1.jobstatus IN ('T','W')
  AND j1.jobbytes > 0
  AND j1.name in ('{7}')
  ORDER by j1.starttime DESC
  LIMIT 1
) j0
WHERE j0.jobid NOT IN (
  SELECT j2.priorjobid
  FROM job j2, pool p2
  WHERE p2.poolid = j2.poolid
  AND j2.type IN ('B','C')
  AND j2.jobstatus IN ('T','W')
  AND j2.priorjobid != 0
  AND p2.name='{6}'
);"
}}""".format(
    copy_job_name,
    CONF('ADD_COPY_JOB_POOL'),
    self.fd_fqdn,
    CONF('ADD_COPY_JOB_JOBDEFS'),
    CONF('ADD_JOB_STORAGE'),
    CONF('ADD_JOB_FILESET'),
    CONF('ADD_COPY_JOB_COPY_POOL'),
    job_name
    )
)
        print("""\
Written following configuration files:\n%s\n\n..Done
""" % (CONF('COPY_JOB_DIR_CONF'))
    )

    def create_filedaemon_files(self):
        """Create filedaemon config and create client encryption keys"""
        # Create the client directory and generates its keys
        self.fd_data_dir = os.path.join(str(pathlib.Path.home()), "bareos-clients", self.fd_fqdn)
        fd_certs_dir = os.path.join(self.fd_data_dir, "certs")
        fd_ssl_key = os.path.join(fd_certs_dir, "%s-fd.key" % self.fd_fqdn)
        fd_ssl_cert = os.path.join(fd_certs_dir, "%s-fd.cert" % self.fd_fqdn)
        fd_ssl_pem = os.path.join(fd_certs_dir, "%s-fd.pem" % self.fd_fqdn)
        subprocess.call(("mkdir -p %s" % fd_certs_dir).split())
        print("..\nCreate the client's private key")
        # Use call() not Popen() to have it wait until the command finished
        subprocess.call(("openssl genrsa -out %s 4096" % fd_ssl_key).split(), stdout=subprocess.PIPE)
        print("Create the certificate from the private key")
        cert_command = ("""\
openssl req -new -key %s -x509 -out %s -subj \
/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com
""" % (fd_ssl_key, fd_ssl_cert)).split()
        p = subprocess.call(cert_command)
        print("Create the client's .pem file: %s" % fd_ssl_pem)
        with open(fd_ssl_pem,'wb') as wfd:
            for f in [fd_ssl_cert, fd_ssl_key]:
                with open(f,'rb') as fd:
                    shutil.copyfileobj(fd, wfd, 1024*1024*10)
        print("Copy %s to %s" % (CONF('MASTER_CERT'), fd_certs_dir))
        shutil.copy(CONF('MASTER_CERT'), fd_certs_dir)

        # Create the filedaemon config files
        fd_myself_conf = os.path.join(self.fd_data_dir, "bareos-fd.d/client/myself.conf")
        fd_bareos_dir_conf = os.path.join(self.fd_data_dir, "bareos-fd.d/director/bareos-dir.conf")
        fd_messages_conf = os.path.join(self.fd_data_dir, "bareos-fd.d/messages/Standard.conf")
        subprocess.call((
            "mkdir -p %s %s %s" % (os.path.dirname(fd_myself_conf),
                                os.path.dirname(fd_bareos_dir_conf),
                                os.path.dirname(fd_messages_conf))
            ).split()
        )
        if self.os_type == "linux":
            keypair_path = "/etc/bareos/certs/%s-fd.pem" % self.fd_fqdn
            masterkey_path = "/etc/bareos/certs/master.cert"
        elif self.os_type == "windows":
            # bareos.fd config wants double backquotes
            keypair_path = "C:\\\\ProgramData\\\\bareos\\\\%s-fd.pem" % self.fd_fqdn
            masterkey_path = "C:\\\\ProgramData\\\\bareos\\\\master.cert"
        with open(fd_myself_conf, "w", encoding='utf8') as f:
            f.write("""
Client {
  Name = %s-fd
  Maximum Concurrent Jobs = 20
  PKI Signatures = Yes
  PKI Encryption = Yes
  PKI Keypair    = "%s"
  PKI Master Key = "%s"
  PKI Cipher     = aes256
}""" % (self.fd_fqdn, keypair_path, masterkey_path))
        # Director resource in bareos-fd.d/director/bareos-dir.conf defines fd password that the
        # director needs to connect to the fd.
        with open(fd_bareos_dir_conf, "w", encoding='utf8') as f:
            f.write("""\
Director {
  Name = %s-dir
  Password = "%s"
  Description = "Allow the configured Director to access this file daemon."
}
""" % (CONF('DIR_FQDN'), self.fd_password))
        with open(fd_messages_conf, "w", encoding='utf8') as f:
            f.write("""
Messages {
  Name = Standard
  Director = %s-dir = all, !skipped, !restored
  Description = "Send relevant messages to the Director."
}
""" % CONF('DIR_FQDN'))
        # Create storage device dir for client and chown to bareos
        subprocess.call(("install -d -m 0755 -o bareos -g bareos %s" % os.path.join(CONF('STORE_CLIENT_FILES'), self.fd_fqdn)).split())

    def generate_password(self):
        # Generating a client password
        process = subprocess.Popen("openssl rand -base64 33".split(), stdout=subprocess.PIPE)
        out, err = process.communicate()
        fd_pw = re.escape(out.split()[0].decode("UTF-8"))
        return fd_pw

    def run(self, dry_run=None, fd_fqdn=None, os_type=None, create_client_job=None, create_client_copy_job=None):
        # User Input
        self.dry_run = dry_run
        self.fd_fqdn = fd_fqdn
        self.os_type = os_type
        self.create_client_job = create_client_job
        self.create_client_copy_job = create_client_copy_job
        self.user_input()
        # Write client and/or job/copy-job resources
        self.dir_conf = bacula_parse("bareos-dir")
        self.fd_password = self.generate_password()
        self.write_client_resource()
        if self.create_client_job:
            self.write_job()
        if self.create_client_copy_job:
            self.write_copy_job()
        # Write filedaemon resources and create client keys
        if not self.client_exists:
            self.create_filedaemon_files()
            print(
                "\nPlease add following certs and config files to your client %s:\n%s" %
                (self.fd_fqdn, self.fd_data_dir)
            )
        print("..DONE")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-r", action="store_true", help="Add client")
    p.add_argument("-fd_fqdn", help="FQDN of the filedaemon you want to add to the director")
    p.add_argument(
        "-os_type",
        help="Specify your client's OS. Supported: linux or windows",
        choices=["linux", "windows"]
    )
    p.add_argument("-create_client_job", help="Create a job for the client?")
    p.add_argument("-create_client_copy_job", help="Create a copy job for the client?")
    p.add_argument("-dry_run", action="store_true", help="Simulate deletion")
    args = p.parse_args()
    if args.r:
        add_client = AddClient()
        add_client.run(
            dry_run=args.dry_run,
            fd_fqdn=args.fd_fqdn,
            os_type=args.os_type,
            create_client_job=args.create_client_job,
            create_client_copy_job=args.create_client_copy_job
        )


if __name__ == "__main__":
    main()
