import os
import tarfile
import datetime
import logging
from dotenv import load_dotenv
import boto3
import sys
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

load_dotenv()

# === Configuration from .env ===
SOURCE_DIR = os.getenv("SOURCE_DIR")
LOG_FILE = os.getenv("LOG_FILE")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/backups")
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "5"))
BACKUP_NAME = os.getenv("BACKUP_NAME", "backup")

# S3 settings
ENABLE_S3_UPLOAD = os.getenv("ENABLE_S3_UPLOAD", "false").lower() == "true"
S3_REGION = os.getenv("S3_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")

# Prometheus Pushgateway
ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false").lower() == "true"
PUSHGATEWAY_URL = os.getenv("PUSHGATEWAY_URL")
PROM_JOB_NAME = os.getenv("JOB_NAME", "backup_job")
PROM_INSTANCE = os.getenv("INSTANCE", "localhost")



# ==== Logging ====
logger = logging.getLogger("generic-backup")
logger.setLevel(logging.INFO)
log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

try:
    log_dir = os.path.dirname(LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)
except Exception as e:
    print(f"[FATAL] Failed to create log directory '{log_dir}': {e}")
    sys.exit(1)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(log_format)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)

if not logger.hasHandlers():
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


def push_status_to_prometheus(status: str, message: str = "", value: int = 1):
    """Push a metric to Prometheus Pushgateway if enabled."""
    if not ENABLE_METRICS:
        return

    try:
        registry = CollectorRegistry()
        g = Gauge('backup_status', 'Status of backup job', ['status', 'message'], registry=registry)
        g.labels(status=status, message=message[:100]).set(value)

        push_to_gateway(
            PUSHGATEWAY_URL,
            job=PROM_JOB_NAME,
            grouping_key={'instance': PROM_INSTANCE},
            registry=registry
        )

        logger.info(f"📊 Prometheus Push: {status} - {message} (value={value})")
    except Exception as e:
        logger.warning(f"⚠️ Failed to push to Prometheus: {e}")

def clean_old_backups():
    try:
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")],
            key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f))
        )
        logger.info(f"Found {len(backups)} backup files in {BACKUP_DIR}")

        if len(backups) <= MAX_BACKUPS:
            logger.info("No cleanup needed, within backup retention limit.")
            push_status_to_prometheus("cleanup", "no cleanup needed", value=0)
            return

        to_delete = backups[:len(backups) - MAX_BACKUPS]
        deleted_count = 0
        for f in to_delete:
            path = os.path.join(BACKUP_DIR, f)
            try:
                os.remove(path)
                logger.info(f"Deleted old backup: {f}")
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {f}: {e}")

        push_status_to_prometheus("cleanup", "old backups cleaned", value=deleted_count)

    except Exception as e:
        logger.warning(f"Could not clean old backups: {e}")

def main():
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create backup directory '{BACKUP_DIR}': {e}")
            sys.exit(1)

        backup_filename = f"{BACKUP_NAME}_{timestamp}.tar.gz"
        backup_path = os.path.join(BACKUP_DIR, backup_filename)

        logger.info(f"Creating backup from: {SOURCE_DIR}")

        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(SOURCE_DIR, arcname=os.path.basename(SOURCE_DIR))
        logger.info(f"Backup file created: {backup_path}")

        if ENABLE_S3_UPLOAD:
            try:
                s3 = boto3.client(
                    "s3",
                    region_name=S3_REGION,
                    aws_access_key_id=S3_ACCESS_KEY,
                    aws_secret_access_key=S3_SECRET_KEY,
                    endpoint_url=os.getenv("S3_ENDPOINT")
                )
        
                s3_key = f"{S3_PREFIX}{backup_filename}"
                s3.upload_file(backup_path, S3_BUCKET, s3_key)
                logger.info(f"☁️  Successfully uploaded to S3: s3://{S3_BUCKET}/{s3_key}")
                push_status_to_prometheus("success", "backup and upload succeeded")
            except Exception as e:
                logger.exception(f"❌ S3 upload failed: {e}")
                push_status_to_prometheus("upload_failed", str(e))
        else:
            logger.info("☁️  S3 upload is disabled (ENABLE_S3_UPLOAD is false)")
            push_status_to_prometheus("success", "backup succeeded (no upload)")

        clean_old_backups()

    except Exception as e:
        logger.exception(f"Error during backup: {e}")
        push_status_to_prometheus("failure", str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()

