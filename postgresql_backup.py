import os
import subprocess
import datetime
import yaml
import logging


class PostgreSQLBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """Accept an instance dict (preferred) or load legacy config.yaml and pick first instance.
        Instance dict keys: name, enabled, host, port, username, password, database, output_dir
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
        self.database = cfg.get('database')
        self.output_dir = cfg.get('output_dir', '/tmp/postgresql_backups')

    def _run_pg_dump(self, timestamp):
        """Run pg_dump command"""
        os.makedirs(self.output_dir, exist_ok=True)

        if self.database:
            # Backup specific database
            output_file = f"{self.output_dir}/postgresql_{self.database}_{timestamp}.sql"
            cmd = ["pg_dump", "--host", self.host, "--port", self.port, "--username", self.username,
                   "--format", "c", "--compress", "9", "--file", output_file, self.database]
        else:
            # Backup all databases (requires superuser)
            output_file = f"{self.output_dir}/postgresql_all_{timestamp}.sql"
            cmd = ["pg_dumpall", "--host", self.host, "--port", self.port, "--username", self.username,
                   "--file", output_file]

        # Set password environment variable
        env = os.environ.copy()
        if self.password:
            env["PGPASSWORD"] = self.password

        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
            self.logger.info("PostgreSQL dump completed successfully")
            return True, None, output_file
        except subprocess.CalledProcessError as e:
            error_msg = f"pg_dump failed: {e.stderr}"
            self.logger.error(error_msg)
            return False, error_msg, None
        except FileNotFoundError:
            error_msg = "pg_dump command not found. Please install PostgreSQL client tools."
            self.logger.error(error_msg)
            return False, error_msg, None

    def run(self):
        """Run the PostgreSQL backup process"""
        if not self.enabled:
            self.logger.info("PostgreSQL backup is disabled")
            return {"status": "disabled", "message": "PostgreSQL backup is disabled"}

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            success, error, output_file = self._run_pg_dump(timestamp)

            if success:
                return {"status": "success", "file": output_file}
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