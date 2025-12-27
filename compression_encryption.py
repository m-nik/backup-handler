import os
import subprocess
import logging
import yaml
import shutil

class CompressionEncryption:
    def __init__(self, config_file=None):
        """Load compression and encryption settings from config.yaml"""
        self.logger = logging.getLogger("compression-encryption")

        if config_file is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_file = os.path.join(base_dir, "config.yaml")

        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        compression_config = config.get('compression', {})
        self.compression_enabled = compression_config.get('enabled', False)
        self.compression_method = compression_config.get('method', '7z')
        self.compression_level = compression_config.get('level', 3)

        encryption_config = compression_config.get('encryption', {})
        self.encryption_enabled = encryption_config.get('enabled', False)
        self.encryption_key = encryption_config.get('key', '')

        self.logger.info(f"Compression: {self.compression_enabled} ({self.compression_method}, level {self.compression_level})")
        self.logger.info(f"Encryption: {self.encryption_enabled} (key from config)")

    # def _compress_file(self, input_file, output_file):
    #     """Compress input_file to output_file using specified method"""
    #     if self.compression_method == 'zstd':
    #         cmd = ['zstd', f'-{self.compression_level}', input_file, '-o', output_file]
    #     elif self.compression_method == 'gzip':
    #         cmd = ['gzip', '-c', input_file, '>', output_file]
    #     elif self.compression_method == 'bzip2':
    #         cmd = ['bzip2', '-c', input_file, '>', output_file]
    #     elif self.compression_method == 'xz':
    #         cmd = ['xz', '-c', input_file, '>', output_file]
    #     else:
    #         raise ValueError(f"Unsupported compression method: {self.compression_method}")

    #     try:
    #         result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    #         self.logger.info(f"Compressed {input_file} to {output_file} using {self.compression_method}")
    #         return True
    #     except subprocess.CalledProcessError as e:
    #         self.logger.error(f"Compression failed: {e.stderr}")
    #         return False
    #     except FileNotFoundError:
    #         self.logger.error(f"Compression tool {self.compression_method} not found")
    #         return False

    def process_file(self, input_file, enabled_compression=False):
        """Process file: compress and encrypt using 7z if enabled. Returns final output file path."""
        if not enabled_compression:
            return input_file  # No processing needed

        key = self.encryption_key
        if not key:
            self.logger.warning(f"Encryption key not found in config, skipping compression and encryption")
            return input_file

        level = self.compression_level

        # Use 7z for compression and encryption
        output_file = input_file + '.7z'
        cmd = ['7z', 'a', '-t7z', '-mhe=on', '-p' + key, '-mx' + str(level), output_file, input_file]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            self.logger.info(f"Compressed and encrypted {input_file} to {output_file} using 7z")
            # Remove original file
            if os.path.isfile(input_file):
                os.remove(input_file)
            elif os.path.isdir(input_file):
                shutil.rmtree(input_file)
            os.remove(input_file)
            return output_file
        except subprocess.CalledProcessError as e:
            self.logger.error(f"7z compression/encryption failed: {e.stderr}")
            return input_file


# For standalone testing
if __name__ == "__main__":
    ce = CompressionEncryption()
    # Test with a sample file
    print("CompressionEncryption module loaded")