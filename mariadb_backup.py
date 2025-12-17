import os
import subprocess
import datetime
import yaml
import logging


class MariaDBBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """Accept an instance dict (preferred) or load legacy config.yaml and pick first instance.
        Instance dict keys: name, enabled, host, port, username, password, databases, output_dir
        """
        self.logger = logging.getLogger("mariadb-backup")

        if instance:
            cfg = instance
        else:
            if config_file is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(base_dir, "config.yaml")
            with open(config_file, 'r') as f:
                cfg_all = yaml.safe_load(f)
            mariadb_section = cfg_all.get('mariadb', {}) or {}
            instances = mariadb_section.get('instances') if isinstance(mariadb_section, dict) else None
            if instances and isinstance(instances, list) and len(instances) > 0:
                cfg = instances[0]
            else:
                cfg = mariadb_section

        self.enabled = cfg.get('enabled', False)
        self.host = cfg.get('host', 'localhost')
        self.port = str(cfg.get('port', '3306'))
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.databases = cfg.get('databases', [])
        self.output_dir = cfg.get('output_dir', '/tmp/mariadb_backups')

    def _run_mysqldump(self, timestamp):
        """Run mysqldump command for specified databases or all if none specified"""
        os.makedirs(self.output_dir, exist_ok=True)

        output_files = []

        if self.databases:
            # Backup specific databases
            for db in self.databases:
                output_file = f"{self.output_dir}/mariadb_{db}_{timestamp}.sql"
                cmd = ["mysqldump", f"--host={self.host}", f"--port={self.port}", f"--user={self.username}",
                       f"--password={self.password}", "--single-transaction", "--routines", "--triggers",
                       "--result-file", output_file, db]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    self.logger.info(f"MariaDB dump completed for database: {db}")
                    output_files.append(output_file)
                except subprocess.CalledProcessError as e:
                    error_msg = f"mysqldump failed for {db}: {e.stderr}"
                    self.logger.error(error_msg)
                    return False, error_msg, None
                except FileNotFoundError:
                    error_msg = "mysqldump command not found. Please install MariaDB/MySQL client tools."
                    self.logger.error(error_msg)
                    return False, error_msg, None
        else:
            # Backup all databases
            output_file = f"{self.output_dir}/mariadb_all_{timestamp}.sql"
            cmd = ["mysqldump", f"--host={self.host}", f"--port={self.port}", f"--user={self.username}",
                   f"--password={self.password}", "--single-transaction", "--routines", "--triggers",
                   "--all-databases", "--result-file", output_file]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info("MariaDB dump completed for all databases")
                output_files.append(output_file)
            except subprocess.CalledProcessError as e:
                error_msg = f"mysqldump failed: {e.stderr}"
                self.logger.error(error_msg)
                return False, error_msg, None
            except FileNotFoundError:
                error_msg = "mysqldump command not found. Please install MariaDB/MySQL client tools."
                self.logger.error(error_msg)
                return False, error_msg, None

        return True, None, output_files

    def run(self):
        """Run the MariaDB backup process"""
        if not self.enabled:
            self.logger.info("MariaDB backup is disabled")
            return {"status": "disabled", "message": "MariaDB backup is disabled"}

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            success, error, output_file = self._run_mysqldump(timestamp)

            if success:
                return {"status": "success", "files": output_files}
            else:
                return {"status": "error", "message": error}
        except Exception as e:
            self.logger.exception(f"MariaDB backup failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    backup = MariaDBBackup()
    result = backup.run()
    print(f"MariaDB backup result: {result}")