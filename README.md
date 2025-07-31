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

The script reads settings from a `config.ini` file in the same directory. Below is an example configuration file with explanations:

```ini
[backup]
# Directory to backup (source data)
source_dir = /path/to/data

# Directory to store local backup files
backup_dir = /path/to/backups

# Base name for backup files; timestamp and .tar.gz extension will be appended automatically
backup_name = my_backup

# How many backup files to keep locally; older backups are deleted automatically
max_backups = 5

[s3]
# Enable uploading backups to S3-compatible storage (true/false)
enabled = true

# MinIO region (can be any string, optional)
region = us-east-1

# S3 bucket name in MinIO
bucket = my-backup-bucket

# Prefix (folder path in bucket)
prefix = backups/

# Access credentials (from MinIO)
access_key = minioadmin
secret_key = minioadmin

# MinIO endpoint URL (usually looks like this if self-hosted locally)
endpoint = http://localhost:9000

[logging]
# Path to the log file where the script writes info and errors
log_file = /var/log/backup_script/backup.log

[metrics]
# Enable Prometheus Pushgateway metrics reporting (true/false)
enabled = true

# URL of Prometheus Pushgateway (e.g., http://localhost:9091)
pushgateway_url = http://localhost:9091

# Job name to use in Prometheus metrics
job_name = backup_job

# Instance label (usually hostname or server id)
instance = myserver01
```

---

## How It Works

* The script creates a compressed tarball (`.tar.gz`) backup of the folder specified in `source_dir`.
* Backups are saved locally in `backup_dir` with filenames like `my_backup_2025-07-31_10-00-00.tar.gz`.
* It keeps only the latest `max_backups` files locally and deletes older backups automatically.
* If S3 upload is enabled, it uploads the backup file to the configured S3 bucket and prefix.
* If metrics are enabled, the script sends backup status metrics to the Prometheus Pushgateway, including success/failure, upload status, and cleanup results.
* Logs are saved both to a file and the console for easy monitoring.

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
* For S3 uploads, ensure your credentials and bucket permissions are correct.
* Prometheus Pushgateway should be accessible from the machine running this script if metrics are enabled.
* You can disable S3 uploads or metrics by setting `enabled = false` under the respective sections.

---
---

## 📄 License

MIT

