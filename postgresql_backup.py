import os
import subprocess
import datetime
import yaml
import logging


class PostgreSQLBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """Accept an instance dict (preferred) or load legacy config.yaml and pick first instance.
        Instance dict keys: name, enabled, host, port, username, password, databases, output_dir
        """
        self.logger = logging.getLogger("postgresql-backup")

        if instance:
            cfg = instance
        else:
            if config_file is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(base_dir, "config.yaml")
            with open(config_file, 'r') as f:
                cfg_all = yaml.safe_load(f)
            pg_section = cfg_all.get('postgresql', {}) or {}
            instances = pg_section.get('instances') if isinstance(pg_section, dict) else None
            if instances and isinstance(instances, list) and len(instances) > 0:
                cfg = instances[0]
            else:
                cfg = pg_section

        self.enabled = cfg.get('enabled', False)
        self.host = cfg.get('host', 'localhost')
        self.port = str(cfg.get('port', '5432'))
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.databases = cfg.get('databases', [])
        self.output_dir = cfg.get('output_dir', '/tmp/postgresql_backups')

        self.logger.info(f"Initialized PostgreSQL backup for {self.host}:{self.port}, Databases: {self.databases or 'all'}")

    def _run_pg_dump(self, timestamp):
        """Run pg_dump command for specified databases or all if none specified"""
        self.logger.info("Starting PostgreSQL dump...")
        os.makedirs(self.output_dir, exist_ok=True)

        # Set password environment variable
        env = os.environ.copy()
        if self.password:
            env["PGPASSWORD"] = self.password

        output_files = []

        if self.databases:
            # Backup specific databases
            for db in self.databases:
                output_file = f"{self.output_dir}/postgresql_{db}_{timestamp}.sql"
                cmd = ["pg_dump", "--host", self.host, "--port", self.port, "--username", self.username,
                       "--format", "c", "--compress", "9", "--file", output_file, db]
                try:
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                    self.logger.info(f"PostgreSQL dump completed for database: {db}")
                    output_files.append(output_file)
                except subprocess.CalledProcessError as e:
                    error_msg = f"pg_dump failed for {db}: {e.stderr}"
                    self.logger.error(error_msg)
                    return False, error_msg, None
                except FileNotFoundError:
                    error_msg = "pg_dump command not found. Please install PostgreSQL client tools."
                    self.logger.error(error_msg)
                    return False, error_msg, None
        else:
            # Backup all databases (requires superuser)
            output_file = f"{self.output_dir}/postgresql_all_{timestamp}.sql"
            cmd = ["pg_dumpall", "--host", self.host, "--port", self.port, "--username", self.username,
                   "--file", output_file]
            try:
                result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
                self.logger.info("PostgreSQL dump completed for all databases")
                output_files.append(output_file)
            except subprocess.CalledProcessError as e:
                error_msg = f"pg_dumpall failed: {e.stderr}"
                self.logger.error(error_msg)
                return False, error_msg, None
            except FileNotFoundError:
                error_msg = "pg_dumpall command not found. Please install PostgreSQL client tools."
                self.logger.error(error_msg)
                return False, error_msg, None

        return True, None, output_files

    def run(self):
        """Run the PostgreSQL backup process"""
        self.logger.info("Starting PostgreSQL backup process")
        if not self.enabled:
            self.logger.info("PostgreSQL backup is disabled")
            return {"status": "disabled", "message": "PostgreSQL backup is disabled"}

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            success, error, output_files = self._run_pg_dump(timestamp)

            if success:
                self.logger.info("PostgreSQL backup completed successfully")
                return {"status": "success", "files": output_files}
            else:
                return {"status": "error", "message": error}
        except Exception as e:
            self.logger.exception(f"PostgreSQL backup failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    backup = PostgreSQLBackup()
    result = backup.run()
    print(f"PostgreSQL backup result: {result}")