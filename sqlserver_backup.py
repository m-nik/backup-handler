import os
import subprocess
import datetime
import yaml
import logging


class SQLServerBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """Accept an instance dict (preferred) or load legacy config.yaml and pick first instance.
        Instance dict keys: name, enabled, host, port, username, password, databases,
        output_dir, trust_server_certificate, sqlpackage_path
        """
        self.logger = logging.getLogger("sqlserver-backup")

        if instance:
            cfg = instance
        else:
            if config_file is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                config_file = os.path.join(base_dir, "config.yaml")
            with open(config_file, 'r') as f:
                cfg_all = yaml.safe_load(f)
            sqlserver_section = cfg_all.get('sqlserver', {}) or {}
            instances = sqlserver_section.get('instances') if isinstance(sqlserver_section, dict) else None
            if instances and isinstance(instances, list) and len(instances) > 0:
                cfg = instances[0]
            else:
                cfg = sqlserver_section

        self.enabled = cfg.get('enabled', False)
        self.host = cfg.get('host', 'localhost')
        self.port = str(cfg.get('port', '1433'))
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.databases = cfg.get('databases', [])
        self.output_dir = cfg.get('output_dir', '/tmp/sqlserver_backups')
        # self-signed certs are common on internal sql servers
        self.trust_server_certificate = cfg.get('trust_server_certificate', True)
        # optional custom path to the sqlpackage binary
        self.sqlpackage_path = cfg.get('sqlpackage_path', 'sqlpackage')

        self.logger.info(f"Initialized SQL Server backup for {self.host}:{self.port}, Databases: {self.databases or 'all'}")

    def _conn_string(self, database):
        cs = (
            f"Server={self.host},{self.port};"
            f"Database={database};"
            f"User Id={self.username};"
            f"Password={self.password};"
        )
        if self.trust_server_certificate:
            cs += "TrustServerCertificate=True;"
        return cs

    def _run_sqlpackage(self, timestamp):
        """Run sqlpackage Export for each database into a .bacpac file.
        Note: sqlpackage has no export-all option, so at least one database
        must be listed in the config."""
        self.logger.info("Starting SQL Server export...")
        os.makedirs(self.output_dir, exist_ok=True)

        if not self.databases:
            return False, "No databases specified. sqlpackage cannot export all databases at once, list them under 'databases'.", None

        output_files = []

        for db in self.databases:
            output_file = os.path.join(self.output_dir, f"sqlserver_{db}_{timestamp}.bacpac")
            cmd = [
                self.sqlpackage_path,
                "/Action:Export",
                f"/SourceConnectionString:{self._conn_string(db)}",
                f"/TargetFile:{output_file}",
                "/Quiet:True",
            ]
            try:
                subprocess.run(cmd, capture_output=True, text=True, check=True)
                self.logger.info(f"SQL Server export completed for database: {db}")
                output_files.append(output_file)
            except subprocess.CalledProcessError as e:
                # stderr/stdout can both hold the error details depending on /Quiet
                detail = (e.stderr or e.stdout or "").strip()
                error_msg = f"sqlpackage failed for {db}: {detail}"
                self.logger.error(error_msg)
                return False, error_msg, None
            except FileNotFoundError:
                error_msg = "sqlpackage command not found. Install Microsoft sqlpackage (dotnet tool or standalone zip from https://learn.microsoft.com/sql/tools/sqlpackage/sqlpackage-download)."
                self.logger.error(error_msg)
                return False, error_msg, None

        return True, None, output_files

    def run(self):
        """Run the SQL Server backup process"""
        self.logger.info("Starting SQL Server backup process")
        if not self.enabled:
            self.logger.info("SQL Server backup is disabled")
            return {"status": "disabled", "message": "SQL Server backup is disabled"}

        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            success, error, output_files = self._run_sqlpackage(timestamp)

            if success:
                self.logger.info("SQL Server backup completed successfully")
                return {"status": "success", "files": output_files}
            else:
                return {"status": "error", "message": error}
        except Exception as e:
            self.logger.exception(f"SQL Server backup failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    backup = SQLServerBackup()
    result = backup.run()
    print(f"SQL Server backup result: {result}")
