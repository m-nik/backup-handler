import os
import subprocess
import datetime
import yaml
import logging


class MongoDBBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """If `instance` dict is provided use it, otherwise load defaults from config.yaml.
        Instance dict should include keys: name, enabled, host, port, username, password, databases, auth_db, output_dir
        """
        self.logger = logging.getLogger("mongodb-backup")

        if instance:
            cfg = instance
        else:
            if config_file is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(base_dir, "config.yaml")
            with open(config_file, 'r') as f:
                cfg_all = yaml.safe_load(f)
            # Support new schema where mongodb.instances is a list
            mongodb_section = cfg_all.get('mongodb', {}) or {}
            instances = mongodb_section.get('instances') if isinstance(mongodb_section, dict) else None
            if instances and isinstance(instances, list) and len(instances) > 0:
                cfg = instances[0]
            else:
                # fallback to older single-mapping keys
                cfg = mongodb_section

        # Populate attributes with instance values or sensible defaults
        self.enabled = cfg.get('enabled', False)
        self.host = cfg.get('host', 'localhost')
        self.port = str(cfg.get('port', '27017'))
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.databases = cfg.get('databases', [])
        self.auth_db = cfg.get('auth_db', 'admin')
        self.output_dir = cfg.get('output_dir', '/tmp/mongodb_backups')

        self.logger.info(f"Initialized MongoDB backup for {self.host}:{self.port}, Databases: {self.databases or 'all'}")

    def _run_mongodump(self, timestamp):
        """Run mongodump command for specified databases or all if none specified"""
        self.logger.info("Starting MongoDB dump...")
        os.makedirs(self.output_dir, exist_ok=True)

        base_cmd = ["mongodump", "--host", self.host, "--port", self.port, "--out", f"{self.output_dir}/mongodb_backup_{timestamp}"]

        if self.username and self.password:
            base_cmd.extend(["--username", self.username, "--password", self.password, "--authenticationDatabase", self.auth_db])

        if self.databases:
            # Dump specific databases
            for db in self.databases:
                cmd = base_cmd + ["--db", db]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    self.logger.info(f"MongoDB dump completed for database: {db}")
                except subprocess.CalledProcessError as e:
                    error_msg = f"mongodump failed for {db}: {e.stderr}"
                    self.logger.error(error_msg)
                    return False, error_msg
                except FileNotFoundError:
                    error_msg = "mongodump command not found. Please install MongoDB tools."
                    self.logger.error(error_msg)
                    return False, error_msg
        else:
            # Dump all databases
            cmd = base_cmd
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info("MongoDB dump completed for all databases")
            except subprocess.CalledProcessError as e:
                error_msg = f"mongodump failed: {e.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
            except FileNotFoundError:
                error_msg = "mongodump command not found. Please install MongoDB tools."
                self.logger.error(error_msg)
                return False, error_msg

        return True, None

    def run(self):
        """Run the MongoDB backup process"""
        self.logger.info("Starting MongoDB backup process")
        if not self.enabled:
            self.logger.info("MongoDB backup is disabled")
            return {"status": "disabled", "message": "MongoDB backup is disabled"}

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            success, error = self._run_mongodump(timestamp)

            if success:
                backup_path = f"{self.output_dir}/mongodb_backup_{timestamp}"
                self.logger.info("MongoDB backup completed successfully")
                return {"status": "success", "path": backup_path}
            else:
                return {"status": "error", "message": error}
        except Exception as e:
            self.logger.exception(f"MongoDB backup failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    backup = MongoDBBackup()
    result = backup.run()
    print(f"MongoDB backup result: {result}")