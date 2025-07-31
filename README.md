# Generic Backup to S3

A minimal and flexible Python script to compress any directory into a `.tar.gz` archive, upload it to an S3-compatible storage, and retain only the latest `N` backups locally.

---

## ✨ Features

- Backup any directory (configurable via `.env`)
- Upload to any S3-compatible service (AWS, MinIO, etc.)
- Retain last `N` local backups
- Full logging to file and stdout
- Simple `.env` configuration
- Cron-friendly

---

## ⚙️ Requirements

- Python 3.8+
- pip packages (see `requirements.txt`)

---

## 📦 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
````

---

## 📝 Configuration

Create a `.env` file like this:

```ini
# Source directory to back up
SOURCE_DIR=/path/to/data

# Directory where backup .tar.gz files are stored temporarily
BACKUP_DIR=/path/to/backups

# Log file location
LOG_FILE=/var/log/generic-backup/backup.log

# Number of backup files to keep locally
MAX_BACKUPS=5

# Base name for the backup file (e.g. mydata_2025-08-01_12-00-00.tar.gz)
BACKUP_NAME=mydata

# S3-compatible storage configuration
ENABLE_S3_UPLOAD=true
S3_REGION=myregion
S3_BUCKET=my-backup-bucket
S3_PREFIX=daily/
S3_ACCESS_KEY=YOUR_S3_ACCESS_KEY
S3_SECRET_KEY=YOUR_S3_SECRET_KEY
S3_ENDPOINT=https://s3.minio.site.com

# Prometheus metrics configurations
ENABLE_METRICS=true
PUSHGATEWAY_URL=http://localhost:9091
JOB_NAME=backup_job
INSTANCE=my-backup-node01
```

---

## 🛠 Usage

Run the script manually:

```bash
source .venv/bin/activate
python backup.py
```

---

## ⏰ Cron Example 

### Example cron file: `/etc/cron.d/backup`

```cron
# Weekly backup every Monday at 03:00
0 3 * * 1 user /home/user/backup/.venv/bin/python /home/user/backup/backup.py
````

**Notes:**

* Replace `user` with the appropriate username that should run the backup.
* Make sure the paths to the Python interpreter and the script are correct.
* After creating the file, set the correct permissions:

```bash
sudo chmod 644 /etc/cron.d/backup
sudo chown root:root /etc/cron.d/backup
```

* The cron daemon will automatically read this file and schedule the job.

---

## 🔒 Notes

* Ensure write permissions for `BACKUP_DIR` and `LOG_FILE`.
* Make sure `.env` file is protected (`chmod 600` recommended).

---

## 📄 License

MIT

