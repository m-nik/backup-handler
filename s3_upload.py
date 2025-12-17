import os
import yaml
import boto3
import logging


class S3Uploader:
    def __init__(self, config_file=None):
        self.logger = logging.getLogger("s3-uploader")

        if config_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "config.yaml")

        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        # Load S3 settings
        s3_config = self.config.get('s3', {})
        self.enabled = s3_config.get('enabled', False)
        self.region = s3_config.get('region')
        self.bucket = s3_config.get('bucket')
        self.prefix = s3_config.get('prefix', "")
        self.access_key = s3_config.get('access_key')
        self.secret_key = s3_config.get('secret_key')
        self.endpoint = s3_config.get('endpoint')

    def upload(self, file_path, file_name):
        """Upload a file to S3"""
        if not self.enabled:
            self.logger.info("S3 upload is disabled")
            return {"status": "disabled", "message": "S3 upload is disabled"}

        try:
            s3 = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                endpoint_url=self.endpoint
            )

            s3_key = f"{self.prefix}{file_name}"
            s3.upload_file(file_path, self.bucket, s3_key)
            self.logger.info(f"Successfully uploaded to S3: s3://{self.bucket}/{s3_key}")
            return {"status": "success", "key": s3_key}
        except Exception as e:
            self.logger.exception(f"S3 upload failed: {e}")
            return {"status": "error", "message": str(e)}


# For standalone execution
if __name__ == "__main__":
    uploader = S3Uploader()
    result = uploader.upload("/path/to/file", "test_file.tar.gz")
    print(f"S3 upload result: {result}")