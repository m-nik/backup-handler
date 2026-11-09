# Backup Handler

A modular Python tool that backs up databases (PostgreSQL, MongoDB, MariaDB, SQL Server, Elasticsearch) and files/folders, compresses and encrypts them with 7z, uploads them to S3-compatible storage (e.g. MinIO), and reports the result to Prometheus.

In one sentence: you configure it once, put it in cron, and every night you get one encrypted `.7z` archive per database in your S3 bucket, with monitoring and old-backup cleanup included.

```
config.yaml ──▶ backup.py ──▶ pg_dump / mongodump / mysqldump / sqlpackage / ES API
                                  │
                                  ▼
                        .sql / dump dir / .bacpac  (per database, in output_dir)
                                  │
                                  ▼
                            7z compress + encrypt (AES-256)
                                  │
                                  ▼
                         upload to MinIO/S3, delete local copy
                                  │
                                  ▼
                    status push to Prometheus Pushgateway
```

## ✨ Features

* Modular backup for multiple database types (PostgreSQL, MongoDB, MariaDB, SQL Server, Elasticsearch)
* Multiple named instances per database type, each with its own credentials and settings
* File/directory backup support
* Compression and encryption using 7z (AES-256)
* Upload to S3-compatible storage (e.g., MinIO, AWS)
* Per-instance compression toggle (`enabled_compression`)
* Retention policy for local file backups and Elasticsearch snapshots
* Prometheus Pushgateway monitoring
* Full logging to file and console
* YAML-based configuration
* CLI with per-instance control
* Cron-friendly

## 📁 Repository Structure — what every file does

| File | Role |
|------|------|
| `backup.py` | **Entry point.** Reads `config.yaml`, parses CLI arguments, runs the selected backups, then routes every produced file through compress → upload → cleanup and collects statuses for Prometheus. Everything else is imported by this file. |
| `postgresql_backup.py` | PostgreSQL backup module. Runs `pg_dump` per database (or `pg_dumpall` for all), one `.sql` file per database into the instance `output_dir`. |
| `mongodb_backup.py` | MongoDB backup module. Runs `mongodump` per database, each into its own directory (`mongodb_<db>_<timestamp>`), or one combined directory in all-databases mode. |
| `mariadb_backup.py` | MariaDB/MySQL backup module. Runs `mysqldump` per database (`--single-transaction --routines --triggers`), one `.sql` file per database. |
| `sqlserver_backup.py` | SQL Server backup module. Runs `sqlpackage /Action:Export` per database, producing one `.bacpac` file per database. |
| `elasticsearch_backup.py` | Elasticsearch backup module. Talks to the ES API: creates the snapshot repository if missing, takes a snapshot of the configured indices, and prunes old snapshots (`retain_snapshot_count`). Supports `fs` and `s3` repository types. |
| `compression_encryption.py` | Turns a dump file/directory into a single password-protected `.7z` archive (AES-256) using the key and level from the `compression` section. |
| `s3_upload.py` | Uploads a file to S3-compatible storage via boto3 (bucket, prefix, endpoint from the `s3` section). |
| `backup_cleaner.py` | Retention for local *file* backups: keeps only the N newest `.tar.gz` files in `backup_dir` (`retention` section). Database dumps are removed right after upload and are not affected. |
| `prometheus_push.py` | Collects statuses during the run (backup ok/failed, upload ok, ...) and pushes them as the `backup_status` gauge to a Prometheus Pushgateway at the end. |
| `config.sample.yaml` | Complete, commented reference of every configuration option. Copy it to `config.yaml` to get started. |
| `requirements.txt` | Python dependencies (boto3, prometheus-client, elasticsearch, PyYAML). |
| `pgdump-backup.sh` | Legacy standalone shell script (docker `pg_dumpall` + 7z) kept from an earlier setup. Not used by `backup.py`. |
| `docs/` | (optional) extra guides. |

Each `*_backup.py` module has the same shape: it takes an instance dict, exposes a `run()` method that returns `{"status": "success"|"error"|"disabled", ...}`, and can also be executed standalone for quick tests (`python3 postgresql_backup.py`). This makes it straightforward to add a new database type: copy one module, adjust the dump command, and wire it into `backup.py`.

## ⚙️ Requirements

* Python 3.8+
* pip packages (see `requirements.txt`)
* Database clients: `pg_dump` (postgresql-client), `mongodump` (mongodb-tools), `mysqldump` (mariadb-client), `sqlpackage` (see [SQL Server](#sql-server))
* Compression/encryption: `7z` (p7zip-full)

### System Dependencies Installation (Ubuntu/Debian)

```bash
# Update package list
sudo apt update

# Install database clients
sudo apt install postgresql-client mongodb-tools mariadb-client

# Install compression tools
sudo apt install p7zip-full
```

### SQL Server

SQL Server backups use `sqlpackage` which must be installed on the machine running this tool:

```bash
sudo mkdir -p /opt/sqlpackage && cd /opt/sqlpackage
sudo curl -sL https://go.microsoft.com/fwlink/?linkid=2316314 -o sqlpackage.zip
sudo unzip sqlpackage.zip && sudo chmod +x sqlpackage
sudo ln -sf /opt/sqlpackage/sqlpackage /usr/local/bin/sqlpackage
```

Notes:
* `sqlpackage` cannot export all databases at once — every instance must list its databases explicitly.
* `sqlpackage` requires .NET runtime; the standalone zip for Linux x64 bundles what it needs.
* Orphaned database users (users without a matching server login, e.g. leftovers from a dev restore) make the export fail with `Error SQL71564`. Fix them on the server (`DROP USER`, or `ALTER USER ... WITH LOGIN = ...`) before backing up.

## 📦 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 📝 Configuration

Copy `config.sample.yaml` to `config.yaml` (next to `backup.py`) and edit it. A minimal but realistic example:

```yaml
s3:
  enabled: true
  region: us-east-1
  bucket: my-backup-bucket
  prefix: myapp/
  access_key: minioadmin
  secret_key: minioadmin
  endpoint: http://minio.local:9000

logging:
  log_file: ./backup.log
  handlers: ['console', 'file']

compression:
  enabled: true
  level: 3
  encryption:
    enabled: true
    key: "a-long-random-secret"

metrics:
  enabled: true
  pushgateway_url: http://prom-push.local:9091
  job_name: backup_job
  instance: server01

postgresql:
  instances:
    - name: main-pg
      enabled: true
      enabled_compression: true
      host: db.local
      port: 5432
      username: backup_user
      password: secret
      databases: [app_db]
      output_dir: /var/lib/backup-handler/postgresql
```

Every database type (`mongodb`, `mariadb`, `sqlserver`, `elasticsearch`) follows the same `instances:` list pattern — see `config.sample.yaml` for all their options.

Key concepts:

| Option | Meaning |
|--------|---------|
| `backup.source_dir` / `backup.backup_dir` | Directory you back **up** (input) / where local `.tar.gz` file backups are **written** (output) |
| `output_dir` (per instance) | **Temporary** location on this machine for dumps before compress/upload; files are deleted after upload, so it needs roughly the size of the largest database |
| `databases: []` | "all databases" for PostgreSQL/MongoDB/MariaDB. SQL Server always requires an explicit list |
| `enabled_compression` (per instance) | Whether this instance's dumps get the 7z compress+encrypt treatment |
| `retain_snapshot_count` (elasticsearch) | Keep only the N newest snapshots in the repository; 0 disables cleanup |
| `retention.retain_file_count` | Keep only the N newest local `.tar.gz` file backups |
| `s3.bucket` | Also used as the default bucket for Elasticsearch `s3` repositories when the instance doesn't set one |

## 🛠 Usage

```bash
source .venv/bin/activate

# Run all enabled backups (files + all enabled DB instances)
python3 backup.py --all

# Only back up files (source_dir)
python3 backup.py --files

# Back up one database type (all enabled instances)
python3 backup.py --postgresql
python3 backup.py --mongodb
python3 backup.py --mariadb
python3 backup.py --sqlserver
python3 backup.py --es

# Back up specific instances (comma-separated names)
python3 backup.py --postgresql main-pg
```

Running without arguments behaves like `--all`.

A successful run looks like this in the log:

```
2026-09-19 09:33:25 [INFO] Initialized SQL Server backup for 192.168.71.15:4004, Databases: ['app_casie_db']
2026-09-19 09:33:38 [INFO] SQL Server export completed for database: app_casie_db
2026-09-19 09:33:41 [INFO] Compressed and encrypted /var/lib/backup-handler/sqlserver/sqlserver_app_casie_db_....bacpac to ....bacpac.7z using 7z
2026-09-19 09:33:43 [INFO] Successfully uploaded to S3: s3://my-backup-bucket/myapp/sqlserver_app_casie_db_....bacpac.7z
```

## 🚀 How It Works

1. Reads `config.yaml` and runs the selected targets (enabled instances only)
2. Database dumps are written per database to the instance `output_dir`
   * PostgreSQL/MariaDB: one `.sql` file per database
   * MongoDB: one dump directory per database (`mongodb_<db>_<timestamp>`)
   * SQL Server: one `.bacpac` file per database
3. Each dump is compressed and encrypted into a `.7z` archive (when `enabled_compression` is set)
4. Archives are uploaded to S3 (when `s3.enabled`) and removed locally after a successful upload
5. Elasticsearch takes snapshots through its API
6. Old local file backups are cleaned based on the retention policy
7. Statuses are pushed to Prometheus Pushgateway

**End result:** one `<dbtype>_<database>_<timestamp>.7z` archive per database in your S3 bucket (under `prefix`), nothing left behind locally except logs, and a `backup_status` metric in the Pushgateway summarising what succeeded or failed.

## ⏰ Cron Example

```cron
# Backup every day at 03:00 AM
0 3 * * * root /opt/backup-handler/.venv/bin/python /opt/backup-handler/backup.py --all >> /opt/backup-handler/cron.log 2>&1
```

No venv activation is needed in cron — call the venv's python binary directly. Verify the exact command works in cron's bare environment first:

```bash
env -i /opt/backup-handler/.venv/bin/python /opt/backup-handler/backup.py --all
```

## 🔐 Restore Instructions

Backup archives are `.7z` files (compressed and encrypted with the key from `compression.encryption.key`).

1. **Extract backup**:

   ```bash
   7z x -p"your_key_from_config" backup_file.7z
   ```

2. **Restore database**:
   * PostgreSQL: `psql -h host -U user -d db < backup.sql`
   * MongoDB: `mongorestore --host host --db db backup_dir/<db>`
   * MariaDB: `mysql -h host -u user -p db < backup.sql`
   * SQL Server: `sqlpackage /Action:Import /SourceFile:backup.bacpac /TargetConnectionString:"Server=host,port;Database=db;User Id=user;Password=pass;TrustServerCertificate=True"`
   * Elasticsearch: restore the snapshot through the ES API

## 🔧 Troubleshooting

### Common Issues

* **7z not found**: Install `p7zip-full` (`apt install p7zip-full` on Ubuntu)
* **Database connection failed**: Check host, port, credentials in config.yaml
* **S3 upload failed**: Verify endpoint, access keys, bucket permissions
* **Encryption key missing**: Ensure `key` is set in `compression.encryption` section
* **Permission denied**: Run with appropriate user permissions for backup directories
* **MongoDB `not authorized on config`**: remove internal databases (`config`, `local`) from the instance `databases` list
* **SQL Server `SQL71564` orphaned user**: see [SQL Server](#sql-server) above
* **Elasticsearch `path.repo` / `repository_missing_exception`**: make sure the ES server has `path.repo` set to a writable directory matching the repository `location`
* **Prometheus push `NoneType object is not callable`**: fixed in current versions; make sure the deployed `prometheus_push.py` is up to date

### Logs

Check the file from `logging.log_file` (default `./backup.log`) for detailed error messages. Logs include timestamps and error details.

## TODO

* only use 7z, drop remaining zstd/gzip references in code and config
* postgresql instances are created regardless of the `enabled` flag when selected explicitly
* elasticsearch s3 repository vs fs decision

## Contribute

https://github.com/m-nik/backup-handler
