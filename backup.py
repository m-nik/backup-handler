import os
import tarfile
import datetime
import logging
from dotenv import load_dotenv
import boto3
import sys

load_dotenv()

SOURCE_DIR = os.getenv("SOURCE_DIR")
LOG_FILE = os.getenv("LOG_FILE")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/backups")
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "5"))
BACKUP_NAME = os.getenv("BACKUP_NAME", "backup")
S3_REGION = os.getenv("S3_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")

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

def clean_old_backups():
    try:
        backups = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.endswith(".tar.gz")],
            key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f))
        )
        logger.info(f"Found {len(backups)} backup files in {BACKUP_DIR}")

        if len(backups) <= MAX_BACKUPS:
            logger.info("No cleanup needed, within backup retention limit.")
            return

        to_delete = backups[:len(backups) - MAX_BACKUPS]
        for f in to_delete:
            path = os.path.join(BACKUP_DIR, f)
            try:
                os.remove(path)
                logger.info(f"Deleted old backup: {f}")
            except Exception as e:
                logger.warning(f"Failed to delete {f}: {e}")
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

        s3 = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            endpoint_url=S3_ENDPOINT
        )

        s3_key = f"{S3_PREFIX}{backup_filename}"
        s3.upload_file(backup_path, S3_BUCKET, s3_key)
        logger.info(f"Backup uploaded to: s3://{S3_BUCKET}/{s3_key}")

        clean_old_backups()

        logger.info("Backup process completed successfully.")
    except Exception as e:
        logger.exception(f"Error during backup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

