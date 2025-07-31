# Generic Backup to S3

A minimal and flexible Python script to compress any directory into a `.tar.gz` archive, upload it to S3-compatible storage (e.g., MinIO), and retain only the latest `N` backups locally.

---

## ✨ Features

* Backup any directory (configurable via `config.ini`)
* Upload to any S3-compatible service (e.g., MinIO, AWS)
* Retain last `N` local backups
* Prometheus Pushgateway monitoring support (optional)
* Full logging to file and stdout
* Simple INI-based configuration
* Cron-friendly

---

## ⚙️ Requirements

* Python 3.8+
* pip packages (see `requirements.txt`)

---

## 📦 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 📝 Configuration

The script reads settings from a `config.ini` file located in the same directory. Below is a sample configuration with comments:

```ini
[backup]
# Directory to back up
source_dir = /data/to/backup

# Local path where backups will be stored
backup_dir = /var/backups/myapp

# Base name for backup files
backup_name = myapp_backup

# Number of backups to retain locally
max_backups = 5

[s3]
# Enable S3 upload (true/false)
enabled = true

# S3-compatible region (e.g., us-east-1)
region = us-east-1

# S3 bucket name
bucket = my-backup-bucket

# Optional prefix in bucket (folder path)
prefix = backups/

# S3 Access credentials (e.g., for MinIO)
access_key = minioadmin
secret_key = minioadmin

# Endpoint of S3 service (e.g., MinIO)
endpoint = http://localhost:9000

[logging]
# Full path to log file
log_file = /var/log/backup_script/backup.log

[metrics]
# Enable Prometheus Pushgateway (true/false)
enabled = true

# Pushgateway URL
pushgateway_url = http://localhost:9091

# Prometheus job name
job_name = backup_job

# Prometheus instance label (e.g., server01)
instance = server01
```

---

## 🚀 How It Works

* Compresses the folder specified in `source_dir` into a `.tar.gz` file inside `backup_dir`.
* Keeps only the latest `max_backups` files; older ones are deleted.
* If `[s3].enabled = true`, uploads backup to the S3 bucket at the specified path.
* If `[metrics].enabled = true`, pushes status metrics (backup success/failure, upload, cleanup) to a Prometheus Pushgateway.
* All logs are written to both console and the specified log file.

---

## 🛠 Usage

Run manually:

```bash
source .venv/bin/activate
python backup.py
```

---

## ⏰ Cron Example

To schedule the backup automatically:

### Example file: `/etc/cron.d/backup`

```cron
# Backup every day at 03:00 AM
0 3 * * * user /path/to/venv/bin/python /path/to/backup.py
```

**Note:**

* Replace `user` with the actual system username.
* Make sure paths are correct.
* Give the file correct permissions:

```bash
sudo chmod 644 /etc/cron.d/backup
sudo chown root:root /etc/cron.d/backup
```

---

## ✅ Best Practices & Notes

* Make sure the user running the script has write access to `backup_dir` and `log_file`.
* Check that S3 credentials and bucket policies allow uploads.
* The Prometheus Pushgateway must be reachable from the machine running the script.
* You can disable S3 upload or metrics by setting `enabled = false` in the corresponding section.

---

## 📄 License

MIT

---

