# SETTINGS

# DIR_FQDN: Set the FQDN of the director daemon
DIR_FQDN = "bareos01.test01."
# SD_FQDN: Set the FQDN of the storage daemon where to store the backups to
SD_FQDN = "bareos01.test01."
# STORAGE_DEVICE: Storage Device to backup to
STORAGE_DEVICE = "sphserver01"
# MASTER_CERT: Set the location of the master.cert
MASTER_CERT = "/etc/bareos/certs/master.cert"
# STORE_CLIENT_FILES: Path to store the client's filedaemon config files, which are copied to
# the filedaemon manually.
STORE_CLIENT_FILES = "/mnt/smb-clients"

# Paths to your Client, Storage and Device resources. If you put all director resources into the
# same config file, then use the same path for *_DIR_CONF.
CLIENT_DIR_CONF = "/etc/bareos/bareos-dir.d/client/bareos-fd.conf"
JOB_DIR_CONF = "/etc/bareos/bareos-dir.d/job/jobs.conf"
COPY_JOB_DIR_CONF = "/etc/bareos/bareos-dir.d/job/copy-jobs.conf"

# OPTIONAL: ADD_JOB_*: Directives to use for creating the job resources
ADD_JOB_FILESET = "rootfs"
ADD_JOB_JOBDEFS = "st"
ADD_JOB_STORAGE = "sphserver01"

# OPTIONAL: ADD_COPY_JOB_*: Directives to use for creating the copy job resources
ADD_COPY_JOB_POOL = "Full-ST"
ADD_COPY_JOB_COPY_POOL = "Full-ST-Copy01"
ADD_COPY_JOB_JOBDEFS = "copy"
