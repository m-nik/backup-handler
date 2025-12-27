import os
import tarfile
import datetime
import logging
import sys
import yaml
import argparse
from s3_upload import S3Uploader
from prometheus_push import PrometheusPusher
from backup_cleaner import BackupCleaner
from compression_encryption import CompressionEncryption
from elasticsearch_backup import ElasticsearchBackup
from mongodb_backup import MongoDBBackup
from postgresql_backup import PostgreSQLBackup
from mariadb_backup import MariaDBBackup

# === Load config.yaml ===
config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_file, 'r') as f:
    config = yaml.safe_load(f)

# === Configuration ===
backup_config = config.get('backup', {})
SOURCE_DIR = backup_config.get('source_dir')
BACKUP_DIR = backup_config.get('backup_dir', "/tmp/backups")
BACKUP_NAME = backup_config.get('backup_name', "backup")

# Logging
logging_config = config.get('logging', {})
LOG_FILE = logging_config.get('log_file')
LOG_HANDLERS = logging_config.get('handlers', ['file'])

# ==== Logging ====
logger = logging.getLogger("generic-backup")
logger.setLevel(logging.INFO)
log_format = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

if 'file' in LOG_HANDLERS:
    try:
        log_dir = os.path.dirname(LOG_FILE)
        os.makedirs(log_dir, exist_ok=True)
    except Exception as e:
        print(f"[FATAL] Failed to create log directory '{log_dir}': {e}")
        sys.exit(1)

file_handler = logging.FileHandler(LOG_FILE) if 'file' in LOG_HANDLERS else None
if file_handler:
    file_handler.setFormatter(log_format)

console_handler = logging.StreamHandler() if 'console' in LOG_HANDLERS else None
if console_handler:
    console_handler.setFormatter(log_format)

if not logger.hasHandlers():
    if file_handler:
        logger.addHandler(file_handler)
    if console_handler:
        logger.addHandler(console_handler)

# Also add handlers to root logger so all loggers can use them
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if file_handler and file_handler not in root_logger.handlers:
    root_logger.addHandler(file_handler)
if console_handler and console_handler not in root_logger.handlers:
    root_logger.addHandler(console_handler)


def main():
    parser = argparse.ArgumentParser(description="Backup runner. Select targets to back up.")
    parser.add_argument('--all', action='store_true', help='Run all backups (files + all DB instances)')
    parser.add_argument('--files', action='store_true', help='Only back up files (source_dir)')
    parser.add_argument('--es', nargs='?', const='all', help='Elasticsearch instances to backup (comma-separated names) or "all"')
    parser.add_argument('--mongodb', nargs='?', const='all', help='MongoDB instances to backup (comma-separated names) or "all"')
    parser.add_argument('--postgresql', nargs='?', const='all', help='PostgreSQL instances to backup (comma-separated names) or "all"')
    parser.add_argument('--mariadb', nargs='?', const='all', help='MariaDB instances to backup (comma-separated names) or "all"')
    args = parser.parse_args()

    # Determine what to run
    selections = {
        'files': args.files,
        'es': args.es,
        'mongodb': args.mongodb,
        'postgresql': args.postgresql,
        'mariadb': args.mariadb,
        'all': args.all
    }

    def _get_instances(section_name, names_selector):
        """Return a list of instance dicts for a section. names_selector can be None, 'all', or comma-separated names."""
        section = config.get(section_name, {}) or {}
        instances = []
        if isinstance(section, dict) and 'instances' in section and isinstance(section['instances'], list):
            instances = section['instances']
        else:
            # legacy: section may be a dict of settings for single instance
            instances = [section]

        if names_selector is None:
            # return enabled instances
            return [i for i in instances if i.get('enabled', False)]
        if isinstance(names_selector, str) and names_selector.lower() == 'all':
            return instances
        # parse comma separated names
        wanted = {n.strip() for n in str(names_selector).split(',') if n.strip()}
        return [i for i in instances if i.get('name') in wanted]

    try:
        # Initialize modules
        s3_uploader = S3Uploader()
        prometheus_pusher = PrometheusPusher()
        backup_cleaner = BackupCleaner()
        compression_encryption = CompressionEncryption()

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create backup directory '{BACKUP_DIR}': {e}")
            sys.exit(1)

        # Determine selection behavior
        has_any = any([selections['all'], selections['files'], selections['es'], selections['mongodb'], selections['postgresql'], selections['mariadb']])
        backup_enabled = config['backup'].get('enabled', False)
        run_files = (selections['all'] or selections['files'] or not has_any) and backup_enabled
        run_all_dbs = selections['all'] or not has_any

        # Files backup
        if run_files:
            backup_filename = f"{BACKUP_NAME}_{timestamp}.tar.gz"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)

            logger.info(f"========================")
            logger.info(f"Creating backup from: {SOURCE_DIR}")

            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(SOURCE_DIR, arcname=os.path.basename(SOURCE_DIR))
            logger.info(f"Backup file created: {backup_path}")
            prometheus_pusher.update_status("backup", "backup succeeded", 1)

            # Upload to S3
            s3_result = s3_uploader.upload(backup_path, backup_filename)
            if s3_result["status"] == "success":
                prometheus_pusher.update_status("upload", f"uploaded {s3_result['key']}", 1)
            elif s3_result["status"] == "disabled":
                prometheus_pusher.update_status("upload", "S3 upload is disabled")
            else:
                prometheus_pusher.update_status("upload", s3_result["message"])

        # Database backups: for each type, determine instance selectors and run per-instance
        # Elasticsearch
        if selections['all'] or selections['es'] or (not has_any and run_all_dbs):
            es_selector = selections['es'] if selections['es'] else 'all'
            es_instances = _get_instances('elasticsearch', es_selector)
            for inst in es_instances:
                es_backup = ElasticsearchBackup(instance=inst)
                es_result = es_backup.run()
                name = inst.get('name', inst.get('url', 'es'))
                if es_result["status"] == "success":
                    prometheus_pusher.update_status("es_backup", f"{name}: snapshot {es_result['snapshot']} succeeded", 1)
                elif es_result["status"] == "disabled":
                    prometheus_pusher.update_status("es_backup", f"{name}: disabled")
                else:
                    prometheus_pusher.update_status("es_backup", f"{name}: {es_result['message']}")

        # MongoDB
        if selections['all'] or selections['mongodb'] or (not has_any and run_all_dbs):
            mongo_selector = selections['mongodb'] if selections['mongodb'] else 'all'
            mongo_instances = _get_instances('mongodb', mongo_selector)
            for inst in mongo_instances:
                mongodb_backup = MongoDBBackup(instance=inst)
                mongodb_result = mongodb_backup.run()
                name = inst.get('name', inst.get('host', 'mongodb'))
                if mongodb_result["status"] == "success":
                    # If path is a directory, create a tar archive first
                    backup_path = mongodb_result['path']
                    if os.path.isdir(backup_path):
                        tar_path = backup_path + '.tar'
                        with tarfile.open(tar_path, "w") as tar:
                            tar.add(backup_path, arcname=os.path.basename(backup_path))
                        # Remove the directory after archiving
                        import shutil
                        shutil.rmtree(backup_path)
                        backup_path = tar_path
                    # Process compression/encryption
                    enabled_compression = inst.get('enabled_compression', False)
                    final_file = compression_encryption.process_file(backup_path, enabled_compression)
                    # Upload to S3 if file changed
                    if final_file != backup_path:
                        s3_result = s3_uploader.upload(final_file, os.path.basename(final_file))
                        if s3_result["status"] == "success":
                            prometheus_pusher.update_status("mongodb_upload", f"{name}: uploaded {s3_result['key']}", 1)
                            # Remove processed file after upload
                            os.remove(final_file)
                        else:
                            prometheus_pusher.update_status("mongodb_upload", f"{name}: {s3_result['message']}")
                    else:
                        prometheus_pusher.update_status("mongodb_upload", f"{name}: no upload needed")
                    prometheus_pusher.update_status("mongodb_backup", f"{name}: backup to {final_file} succeeded", 1)
                elif mongodb_result["status"] == "disabled":
                    prometheus_pusher.update_status("mongodb_backup", f"{name}: disabled")
                else:
                    prometheus_pusher.update_status("mongodb_backup", f"{name}: {mongodb_result['message']}")

        # PostgreSQL
        if selections['all'] or selections['postgresql'] or (not has_any and run_all_dbs):
            pg_selector = selections['postgresql'] if selections['postgresql'] else 'all'
            pg_instances = _get_instances('postgresql', pg_selector)
            for inst in pg_instances:
                postgresql_backup = PostgreSQLBackup(instance=inst)
                postgresql_result = postgresql_backup.run()
                name = inst.get('name', inst.get('host', 'postgresql'))
                if postgresql_result["status"] == "success":
                    # Process each file
                    for file_path in postgresql_result['files']:
                        enabled_compression = inst.get('enabled_compression', False)
                        final_file = compression_encryption.process_file(file_path, enabled_compression)
                        # Upload to S3 if file changed
                        if final_file != file_path:
                            s3_result = s3_uploader.upload(final_file, os.path.basename(final_file))
                            if s3_result["status"] == "success":
                                prometheus_pusher.update_status("postgresql_upload", f"{name}: uploaded {s3_result['key']}", 1)
                                # Remove processed file after upload
                                os.remove(final_file)
                            else:
                                prometheus_pusher.update_status("postgresql_upload", f"{name}: {s3_result['message']}")
                        else:
                            prometheus_pusher.update_status("postgresql_upload", f"{name}: no upload needed")
                    prometheus_pusher.update_status("postgresql_backup", f"{name}: backup to {postgresql_result['files']} succeeded", 1)
                elif postgresql_result["status"] == "disabled":
                    prometheus_pusher.update_status("postgresql_backup", f"{name}: disabled")
                else:
                    prometheus_pusher.update_status("postgresql_backup", f"{name}: {postgresql_result['message']}")

        # MariaDB
        if selections['all'] or selections['mariadb'] or (not has_any and run_all_dbs):
            maria_selector = selections['mariadb'] if selections['mariadb'] else 'all'
            maria_instances = _get_instances('mariadb', maria_selector)
            for inst in maria_instances:
                mariadb_backup = MariaDBBackup(instance=inst)
                mariadb_result = mariadb_backup.run()
                name = inst.get('name', inst.get('host', 'mariadb'))
                if mariadb_result["status"] == "success":
                    # Process each file
                    for file_path in mariadb_result['files']:
                        enabled_compression = inst.get('enabled_compression', False)
                        final_file = compression_encryption.process_file(file_path, enabled_compression)
                        # Upload to S3 if file changed
                        if final_file != file_path:
                            s3_result = s3_uploader.upload(final_file, os.path.basename(final_file))
                            if s3_result["status"] == "success":
                                prometheus_pusher.update_status("mariadb_upload", f"{name}: uploaded {s3_result['key']}", 1)
                                # Remove processed file after upload
                                os.remove(final_file)
                            else:
                                prometheus_pusher.update_status("mariadb_upload", f"{name}: {s3_result['message']}")
                        else:
                            prometheus_pusher.update_status("mariadb_upload", f"{name}: no upload needed")
                    prometheus_pusher.update_status("mariadb_backup", f"{name}: backup to {mariadb_result['files']} succeeded", 1)
                elif mariadb_result["status"] == "disabled":
                    prometheus_pusher.update_status("mariadb_backup", f"{name}: disabled")
                else:
                    prometheus_pusher.update_status("mariadb_backup", f"{name}: {mariadb_result['message']}")

        # Clean old backups
        clean_result = backup_cleaner.clean()
        if clean_result["status"] == "success":
            prometheus_pusher.update_status("retention", f"cleaned {clean_result['deleted']} files", clean_result["deleted"])
        elif clean_result["status"] == "disabled":
            prometheus_pusher.update_status("retention", "retention disabled")
        elif clean_result["status"] == "no_cleanup_needed":
            prometheus_pusher.update_status("retention", "no cleanup needed")
        else:
            prometheus_pusher.update_status("retention", clean_result["message"])

        # Push metrics to Prometheus
        prometheus_pusher.push()

    except Exception as e:
        logger.exception(f"Error during backup: {e}")
        # Try to push error status if possible
        try:
            prometheus_pusher.update_status("backup", str(e))
            prometheus_pusher.push()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()

