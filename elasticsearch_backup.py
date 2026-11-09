import os
import datetime
import logging
import json
import yaml
from elasticsearch import Elasticsearch, NotFoundError


class ElasticsearchBackup:
    def __init__(self, config_file=None, instance: dict = None):
        """Accept instance dict or load legacy config and pick first instance.
        Instance dict keys: name, enabled, url, repository, snapshot_name, indices, username, password, repository_type, repository_settings
        """
        self.logger = logging.getLogger("elasticsearch-backup")

        # Global s3 settings are always read from config.yaml
        if config_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "config.yaml")
        with open(config_file, 'r') as f:
            cfg_all = yaml.safe_load(f)
        s3_global = cfg_all.get('s3', {}) or {}

        if instance:
            cfg = instance
        else:
            es_section = cfg_all.get('elasticsearch', {}) or {}
            instances = es_section.get('instances') if isinstance(es_section, dict) else None
            if instances and isinstance(instances, list) and len(instances) > 0:
                cfg = instances[0]
            else:
                cfg = es_section

        self.enabled = cfg.get('enabled', False)
        self.url = cfg.get('url', 'http://localhost:9200')
        self.repository = cfg.get('repository', 'backup_repo')
        self.snapshot_name = cfg.get('snapshot_name', 'es_backup')
        self.indices = cfg.get('indices', [])
        self.username = cfg.get('username')
        self.password = cfg.get('password')
        self.repo_type = cfg.get('repository_type', 'fs')
        self.repo_settings = cfg.get('repository_settings', '{}')
        self.retain_snapshot_count = cfg.get('retain_snapshot_count', 0)

        # For s3 repositories, fall back to the global s3 bucket when the
        # instance doesn't specify one, so it doesn't have to be repeated.
        if self.repo_type == 's3' and isinstance(self.repo_settings, dict):
            if not self.repo_settings.get('bucket') and s3_global.get('bucket'):
                self.repo_settings = dict(self.repo_settings)
                self.repo_settings['bucket'] = s3_global['bucket']
                self.logger.info(f"Using bucket '{s3_global['bucket']}' from global s3 config for repository")

        self.logger.info(f"Initialized Elasticsearch backup for URL: {self.url}, Repository: {self.repository}")

    def _connect(self):
        """Establish connection to Elasticsearch"""
        self.logger.info("Connecting to Elasticsearch...")
        es_kwargs = {"hosts": [self.url]}
        if self.username and self.password:
            es_kwargs["basic_auth"] = (self.username, self.password)
        es_client = Elasticsearch(**es_kwargs)
        self.logger.info("Connected to Elasticsearch successfully")
        return es_client

    def _ensure_repository(self, es_client):
        """Create repository if it doesn't exist"""
        try:
            response = es_client.snapshot.get_repository(name=self.repository)
            existing = response.get(self.repository)
            if existing:
                if existing.get('type') != self.repo_type:
                    raise Exception(
                        f"Repository '{self.repository}' already exists with type "
                        f"'{existing.get('type')}' but config says '{self.repo_type}'. "
                        f"Delete the repository or align the config."
                    )
                self.logger.info(f"Elasticsearch repository already exists: {self.repository}")
                return
        except NotFoundError:
            pass

        repo_settings = self.repo_settings
        if isinstance(repo_settings, str):
            repo_settings = json.loads(repo_settings)
        es_client.snapshot.create_repository(
            name=self.repository,
            body={
                "type": self.repo_type,
                "settings": repo_settings
            }
        )
        self.logger.info(f"Created Elasticsearch repository: {self.repository}")

    def _clean_old_snapshots(self, es_client):
        """Delete oldest snapshots beyond retain_snapshot_count (0 disables)"""
        if not self.retain_snapshot_count or self.retain_snapshot_count < 1:
            return 0

        result = es_client.snapshot.get(repository=self.repository, snapshot='*')
        snapshots = result.get('snapshots', [])
        if len(snapshots) <= self.retain_snapshot_count:
            return 0

        snapshots.sort(key=lambda s: s.get('start_time_in_millis', 0))
        to_delete = snapshots[:len(snapshots) - self.retain_snapshot_count]
        for snap in to_delete:
            snap_name = snap.get('snapshot')
            try:
                es_client.snapshot.delete(repository=self.repository, snapshot=snap_name)
                self.logger.info(f"Deleted old Elasticsearch snapshot: {snap_name}")
            except Exception as e:
                self.logger.warning(f"Failed to delete snapshot {snap_name}: {e}")
        return len(to_delete)

    def _create_snapshot(self, es_client):
        """Create a snapshot of specified indices or all if none specified"""
        self.logger.info("Creating Elasticsearch snapshot...")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        snapshot_name = f"{self.snapshot_name}_{timestamp}"

        indices = ",".join(self.indices) if self.indices else "_all"
        self.logger.info(f"Snapshot indices: {indices}")

        try:
            es_client.snapshot.create(
                repository=self.repository,
                snapshot=snapshot_name,
                body={
                    "indices": indices,
                    "ignore_unavailable": True,
                    "include_global_state": False
                },
                wait_for_completion=True
            )
            self.logger.info(f"Elasticsearch snapshot created: {snapshot_name} for indices: {indices}")
            return snapshot_name
        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")
            raise

    def run(self):
        """Run the Elasticsearch backup process"""
        self.logger.info("Starting Elasticsearch backup process")
        if not self.enabled:
            self.logger.info("Elasticsearch backup is disabled")
            return {"status": "disabled", "message": "Elasticsearch backup is disabled"}

        try:
            es_client = self._connect()
            self._ensure_repository(es_client)
            snapshot_name = self._create_snapshot(es_client)
            deleted = self._clean_old_snapshots(es_client)
            self.logger.info("Elasticsearch backup completed successfully")
            return {"status": "success", "snapshot": snapshot_name, "deleted_old_snapshots": deleted}
        except Exception as e:
            self.logger.exception(f"Elasticsearch backup failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    backup = ElasticsearchBackup()
    result = backup.run()
    print(f"Elasticsearch backup result: {result}")