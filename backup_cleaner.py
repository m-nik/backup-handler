import os
import yaml
import logging


class BackupCleaner:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger("backup-cleaner")

        if config_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "config.yaml")

        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load retention settings
        retention_config = self.config.get('retention', {})
        self.enabled = retention_config.get('enable', True)
        self.retain_count = retention_config.get('retain_file_count', 5)

        # Load backup dir from backup config
        backup_config = self.config.get('backup', {})
        self.backup_dir = backup_config.get('backup_dir', "/tmp/backups")

    def clean(self):
        """Clean old backup files based on retention policy"""
        if not self.enabled:
            self.logger.info("Backup retention is disabled; no old files will be deleted.")
            return {"status": "disabled"}

        try:
            backups = sorted(
                [f for f in os.listdir(self.backup_dir) if f.endswith(".tar.gz")],
                key=lambda f: os.path.getmtime(os.path.join(self.backup_dir, f))
            )
            self.logger.info(f"Found {len(backups)} backup files in {self.backup_dir}")

            if len(backups) <= self.retain_count:
                self.logger.info("No retention needed, within backup retention limit.")
                return {"status": "no_cleanup_needed"}

            to_delete = backups[:len(backups) - self.retain_count]
            deleted_count = 0
            for f in to_delete:
                path = os.path.join(self.backup_dir, f)
                try:
                    os.remove(path)
                    self.logger.info(f"Deleted old backup: {f}")
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete {f}: {e}")

            return {"status": "success", "deleted": deleted_count}
        except Exception as e:
            self.logger.warning(f"Could not clean old backups: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    cleaner = BackupCleaner()
    result = cleaner.clean()
    print(f"Backup cleanup result: {result}")