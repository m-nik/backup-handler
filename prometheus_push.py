import os
import yaml
import logging
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from prometheus_client.exposition import basic_auth_handler


class PrometheusPusher:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger("prometheus-pusher")

        if config_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "config.yaml")

        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load Prometheus settings
        metrics_config = self.config.get('metrics', {})
        self.enabled = metrics_config.get('enabled', False)
        self.pushgateway_url = metrics_config.get('pushgateway_url')
        self.job_name = metrics_config.get('job_name', "backup_job")
        self.instance = metrics_config.get('instance', "localhost")
        self.username = metrics_config.get('username')
        self.password = metrics_config.get('password')

        self.status_dict = {}

    def update_status(self, status: str, message: str = "", value: int = 0):
        """Update backup status for Prometheus"""
        truncated_message = message[:100]
        key = (status, truncated_message)
        self.status_dict[key] = value

    def push(self):
        """Push all statuses to Prometheus Pushgateway"""
        if not self.enabled or not self.status_dict:
            return {"status": "disabled" if not self.enabled else "no_data"}

        try:
            registry = CollectorRegistry()
            g = Gauge('backup_status', 'Status of backup job', ['status', 'message'], registry=registry)

            for (status, message), value in self.status_dict.items():
                g.labels(status=status, message=message).set(value)

            if self.username and self.password:
                def handler(url, method, timeout, headers, data):
                    return basic_auth_handler(url, method, timeout, headers, data, self.username, self.password)
            else:
                handler = None

            push_to_gateway(
                self.pushgateway_url,
                job=self.job_name,
                grouping_key={'instance': self.instance},
                registry=registry,
                handler=handler
            )
            self.logger.info(f"Prometheus Push: pushed {len(self.status_dict)} statuses")
            self.status_dict.clear()
            return {"status": "success", "count": len(self.status_dict)}
        except Exception as e:
            self.logger.warning(f"Failed to push to Prometheus: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    pusher = PrometheusPusher()
    pusher.update_status("test", "test message", 1)
    result = pusher.push()
    print(f"Prometheus push result: {result}")