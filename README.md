# Backup Handler

A modular Python script for backing up databases (PostgreSQL, MongoDB, MariaDB, Elasticsearch) and files to local storage with optional S3 upload, compression, encryption, and Prometheus monitoring.

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## ✨ Features

* Modular backup for multiple database types (PostgreSQL, MongoDB, MariaDB, Elasticsearch)
* File/directory backup support
* Compression using zstd, gzip, bzip2, or xz
* Encryption using 7z AES-256
* Upload to S3-compatible storage (e.g., MinIO, AWS)
* Retention policy for local backups
* Prometheus Pushgateway monitoring
* Full logging to file and console
* YAML-based configuration
* CLI with per-instance control
* Cron-friendly

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## ⚙️ Requirements

* Python 3.8+
* pip packages (see `requirements.txt`)
* Database clients: `pg_dump` (postgresql-client), `mongodump` (mongodb-tools), `mysqldump` (mariadb-client), `elasticsearch-dump` (npm install -g @elastic/elasticsearch-dump)
* Compression tools: `zstd`, `gzip`, `bzip2`, `xz`, `7z` (p7zip-full)

### System Dependencies Installation (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install database clients
sudo apt install postgresql-client mongodb-tools mariadb-client

# Install compression tools
sudo apt install zstd gzip bzip2 xz-utils p7zip-full

# Install Node.js for elasticsearch-dump (optional)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install -g @elastic/elasticsearch-dump
```

* For S3: `boto3` (included in requirements.txt)

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 📦 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 📝 Configuration

Copy `config.sample.yaml` to `config.yaml` and edit the settings as needed. The script reads settings from `config.yaml`. Below is a sample configuration with all options:

```yaml
backup:
  source_dir: /data/to/backup
  backup_dir: ./backups
  backup_name: myapp_backup
  enabled: false

retention:
  enable: false
  retain_file_count: 5

s3:
  enabled: false
  region: us-east-1
  bucket: my-backup-bucket
  prefix: backups/
  access_key: minioadmin
  secret_key: minioadmin
  endpoint: http://localhost:9000

logging:
  log_file: ./backup.log
  handlers: ['console', 'file']

compression:
  enabled: false
  method: zstd
  level: 3
  encryption:
    enabled: false
    key: "your_secret_key_here"

metrics:
  enabled: false
  pushgateway_url: http://localhost:9091
  job_name: backup_job
  instance: server01
  username: your_username
  password: your_password

postgresql:
  instances:
    - name: my-pg
      enabled: false
      enabled_compression: true
      host: localhost
      port: 5432
      username: ""
      password: ""
      databases: []
      output_dir: ./backups

mongodb:
  instances:
    - name: my-mongo
      enabled: false
      enabled_compression: true
      host: localhost
      port: 27017
      username: ""
      password: ""
      databases: []
      auth_db: admin
      output_dir: ./backups

mariadb:
  instances:
    - name: my-mariadb
      enabled: false
      enabled_compression: true
      host: localhost
      port: 3306
      username: ""
      password: ""
      databases: []
      output_dir: ./backups

elasticsearch:
  instances:
    - name: my-es
      enabled: false
      url: http://localhost:9200
      repository: my_backup_repo
      snapshot_name: elasticsearch_backup
      indices: []
      username: ""
      password: ""
      repository_type: fs
      repository_settings: {"location": "/var/backups/es"}
```

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🚀 How It Works

* Backs up enabled database instances or files
* Compresses and encrypts backups using 7z if enabled
* Uploads to S3 if configured
* Cleans up old backups based on retention policy
* Pushes metrics to Prometheus if enabled
* Logs all operations

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🛠 Usage

### Manual Run

```bash
source .venv/bin/activate
python backup.py --all
```

### CLI Options

* `--all`: Backup all enabled instances
* `--postgresql <name>`: Backup specific PostgreSQL instance
* `--mongodb <name>`: Backup specific MongoDB instance
* `--mariadb <name>`: Backup specific MariaDB instance
* `--elasticsearch <name>`: Backup specific Elasticsearch instance
* `--files`: Backup files from config

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## ⏰ Cron Example

```cron
# Backup every day at 03:00 AM
0 3 * * * user /path/to/venv/bin/python /path/to/backup.py --all
```

Set environment variable in cron:

```bash
# In crontab
0 3 * * * user /path/to/venv/bin/python /path/to/backup.py --all
```

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🔐 Restore Instructions

Backup files are `.7z` archives (compressed and encrypted).

### Prerequisites
- Install 7z: `apt install p7zip-full`
- Set `BACKUP_KEY` environment variable

### Restore Steps

1. **Extract backup**:
   ```bash
   7z x -p"your_key_from_config" backup_file.7z
   ```

2. **Restore database**:
   - PostgreSQL: `psql -h host -U user -d db < backup.sql`
   - MongoDB: `mongorestore --db db backup_dir`
   - MariaDB: `mysql -h host -u user -p db < backup.sql`

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---


## Contribute

https://github.com/m-nik/backup-handler

```yaml
backup:
  source_dir: /data/to/backup
  backup_dir: ./backups
  backup_name: myapp_backup
  enabled: false

retention:
  enable: false
  retain_file_count: 5

s3:
  enabled: false
  region: us-east-1
  bucket: my-backup-bucket
  prefix: backups/
  access_key: minioadmin
  secret_key: minioadmin
  endpoint: http://localhost:9000

logging:
  log_file: ./backup.log
  handlers: ['console', 'file']

compression:
  enabled: false
  method: zstd
  level: 3
  encryption:
    enabled: false
    key: "your_secret_key_here"

metrics:
  enabled: false
  pushgateway_url: http://localhost:9091
  job_name: backup_job
  instance: server01
  username: your_username
  password: your_password

postgresql:
  instances:
    - name: my-pg
      enabled: false
      enabled_compression: true
      host: localhost
      port: 5432
      username: ""
      password: ""
      databases: []
      output_dir: ./backups

mongodb:
  instances:
    - name: my-mongo
      enabled: false
      enabled_compression: true
      host: localhost
      port: 27017
      username: ""
      password: ""
      databases: []
      auth_db: admin
      output_dir: ./backups

mariadb:
  instances:
    - name: my-mariadb
      enabled: false
      enabled_compression: true
      host: localhost
      port: 3306
      username: ""
      password: ""
      databases: []
      output_dir: ./backups

elasticsearch:
  instances:
    - name: my-es
      enabled: false
      url: http://localhost:9200
      repository: my_backup_repo
      snapshot_name: elasticsearch_backup
      indices: []
      username: ""
      password: ""
      repository_type: fs
      repository_settings: {"location": "/var/backups/es"}
```

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🚀 How It Works

* Backs up enabled database instances or files
* Compresses and encrypts backups using 7z if enabled
* Uploads to S3 if configured
* Cleans up old backups based on retention policy
* Pushes metrics to Prometheus if enabled
* Logs all operations

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🛠 Usage

### Manual Run

```bash
source .venv/bin/activate
python backup.py --all
```

### CLI Options

* `--all`: Backup all enabled instances
* `--postgresql <name>`: Backup specific PostgreSQL instance
* `--mongodb <name>`: Backup specific MongoDB instance
* `--mariadb <name>`: Backup specific MariaDB instance
* `--elasticsearch <name>`: Backup specific Elasticsearch instance
* `--files`: Backup files from config

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## ⏰ Cron Example

```cron
# Backup every day at 03:00 AM
0 3 * * * user /path/to/venv/bin/python /path/to/backup.py --all
```

Set environment variable in cron:

```bash
# In crontab
0 3 * * * user /path/to/venv/bin/python /path/to/backup.py --all
```

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---

## 🔐 Restore Instructions

Backup files are `.7z` archives (compressed and encrypted).

### Prerequisites
- Install 7z: `apt install p7zip-full`
- Set `BACKUP_KEY` environment variable

### Restore Steps

1. **Extract backup**:
   ```bash
   7z x -p"your_key_from_config" backup_file.7z
   ```

2. **Restore database**:
   - PostgreSQL: `psql -h host -U user -d db < backup.sql`
   - MongoDB: `mongorestore --db db backup_dir`
   - MariaDB: `mysql -h host -u user -p db < backup.sql`

---
## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories

### Logs

Check `./backup.log` for detailed error messages. Logs include timestamps and error details.

---


## Contribute

https://github.com/m-nik/backup-handler
