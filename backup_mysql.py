#!/usr/bin/env python3
"""
mysql2docker - Backup MySQL database and bundle into Docker image
Running inside Docker container with Docker socket mounted
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
MYSQL_HOST = os.getenv('MYSQL_HOST')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

DOCKER_USERNAME = os.getenv('DOCKER_USERNAME')
DOCKER_PASSWORD = os.getenv('DOCKER_PASSWORD')
DOCKER_IMAGE_NAME = os.getenv('DOCKER_IMAGE_NAME', 'mysql-backup')
CUSTOM_TAG = os.getenv('CUSTOM_TAG', '')  # Optional custom tag

# Working directory
WORK_DIR = Path('/tmp/mysql2docker')
WORK_DIR.mkdir(exist_ok=True)


def validate_config():
    """Validate required environment variables"""
    required = {
        'MYSQL_HOST': MYSQL_HOST,
        'MYSQL_USER': MYSQL_USER,
        'MYSQL_PASSWORD': MYSQL_PASSWORD,
        'MYSQL_DATABASE': MYSQL_DATABASE,
        'DOCKER_USERNAME': DOCKER_USERNAME,
        'DOCKER_PASSWORD': DOCKER_PASSWORD
    }
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please provide all required environment variables")
        sys.exit(1)


def run_command(cmd, capture_output=False, hide_password=False):
    """Execute shell command and handle errors"""
    try:
        display_cmd = cmd if isinstance(cmd, str) else ' '.join(cmd)
        if hide_password:
            display_cmd = display_cmd.replace(MYSQL_PASSWORD, '***').replace(DOCKER_PASSWORD, '***')
        
        logger.info(f"Running: {display_cmd}")
        
        result = subprocess.run(
            cmd,
            shell=isinstance(cmd, str),
            check=True,
            capture_output=capture_output,
            text=True
        )
        return result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            logger.error(f"Error output: {e.stderr}")
        sys.exit(1)


def backup_mysql(timestamp):
    """Backup MySQL database with mysqldump"""
    backup_file = WORK_DIR / f"backup_{timestamp}.sql"
    backup_gz = WORK_DIR / f"backup_{timestamp}.sql.gz"
    
    logger.info(f"Starting MySQL backup for database: {MYSQL_DATABASE}")
    logger.info(f"Connecting to: {MYSQL_HOST}:{MYSQL_PORT}")
    
    # Build mysqldump command
    cmd = [
        'mysqldump',
        f'-h{MYSQL_HOST}',
        f'-P{MYSQL_PORT}',
        f'-u{MYSQL_USER}',
        f'-p{MYSQL_PASSWORD}',
        '--single-transaction',
        '--quick',
        '--lock-tables=false',
        MYSQL_DATABASE
    ]
    
    try:
        # Dump to file
        logger.info("Executing mysqldump...")
        with open(backup_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE, text=True)
        
        logger.info(f"Backup created: {backup_file.name}")
        
        # Compress with gzip
        logger.info("Compressing backup...")
        run_command(f"gzip {backup_file}")
        
        logger.info(f"Compressed backup: {backup_gz.name}")
        
        # Get file size
        size_mb = backup_gz.stat().st_size / (1024 * 1024)
        logger.info(f"Backup size: {size_mb:.2f} MB")
        
        return backup_gz
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        logger.error(f"MySQL backup failed: {error_msg}")
        if backup_file.exists():
            backup_file.unlink()
        sys.exit(1)


def create_dump_dockerfile(backup_file, timestamp):
    """Create Dockerfile for dump image"""
    dockerfile_content = f"""FROM alpine:latest

LABEL maintainer="mysql2docker"
LABEL description="MySQL backup snapshot"
LABEL backup.timestamp="{timestamp}"
LABEL backup.database="{MYSQL_DATABASE}"
LABEL backup.host="{MYSQL_HOST}"

# Create backup directory
RUN mkdir -p /backups

# Copy backup file
COPY {backup_file.name} /backups/

# Add metadata
RUN echo "Database: {MYSQL_DATABASE}" > /backups/backup_info.txt && \\
    echo "Backup Time: {timestamp}" >> /backups/backup_info.txt && \\
    echo "MySQL Host: {MYSQL_HOST}" >> /backups/backup_info.txt && \\
    echo "Created At: $(date)" >> /backups/backup_info.txt

# Default command to list backups
CMD ["sh", "-c", "echo '=== MySQL Backup Info ===' && cat /backups/backup_info.txt && echo '' && echo '=== Backup Files ===' && ls -lh /backups/*.gz"]
"""
    
    dockerfile_path = WORK_DIR / 'Dockerfile.dump'
    with open(dockerfile_path, 'w') as f:
        f.write(dockerfile_content)
    
    logger.info(f"Created Dockerfile for dump image")
    return dockerfile_path


def docker_login():
    """Login to Docker registry"""
    logger.info(f"Logging in to Docker registry as {DOCKER_USERNAME}...")
    
    cmd = f"echo {DOCKER_PASSWORD} | docker login -u {DOCKER_USERNAME} --password-stdin"
    run_command(cmd, hide_password=True)
    
    logger.info("Docker login successful")


def build_docker_image(timestamp):
    """Build Docker dump image containing the backup"""
    if CUSTOM_TAG:
        image_tag = f"{DOCKER_USERNAME}/{DOCKER_IMAGE_NAME}:{CUSTOM_TAG}"
    else:
        image_tag = f"{DOCKER_USERNAME}/{DOCKER_IMAGE_NAME}:backup_mysql_{timestamp}"
    
    logger.info(f"Building Docker dump image: {image_tag}")
    
    cmd = [
        'docker', 'build',
        '-f', str(WORK_DIR / 'Dockerfile.dump'),
        '-t', image_tag,
        str(WORK_DIR)
    ]
    
    run_command(cmd)
    logger.info(f"Docker image built successfully: {image_tag}")
    
    return image_tag


def push_docker_image(image_tag):
    """Push Docker image to registry"""
    logger.info(f"Pushing image to Docker registry: {image_tag}")
    
    cmd = ['docker', 'push', image_tag]
    run_command(cmd)
    
    logger.info(f"Image pushed successfully: {image_tag}")


def cleanup_local_image(image_tag):
    """Remove local Docker image to save space"""
    logger.info(f"Cleaning up local image: {image_tag}")
    
    try:
        cmd = ['docker', 'rmi', image_tag]
        run_command(cmd)
        logger.info("Local image removed")
    except:
        logger.warning("Failed to remove local image (non-critical)")


def main():
    """Main execution flow"""
    logger.info("=" * 70)
    logger.info("mysql2docker - MySQL Backup to Docker Image (Container Mode)")
    logger.info("=" * 70)
    
    # Validate configuration
    validate_config()
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Backup timestamp: {timestamp}")
    
    try:
        # Step 1: Backup MySQL
        backup_file = backup_mysql(timestamp)
        
        # Step 2: Create Dockerfile for dump image
        create_dump_dockerfile(backup_file, timestamp)
        
        # Step 3: Login to Docker registry
        docker_login()
        
        # Step 4: Build Docker dump image
        image_tag = build_docker_image(timestamp)
        
        # Step 5: Push to Docker registry
        push_docker_image(image_tag)
        
        # Step 6: Cleanup local image
        cleanup_local_image(image_tag)
        
        logger.info("=" * 70)
        logger.info("✓ Backup process completed successfully!")
        logger.info(f"✓ Docker image: {image_tag}")
        logger.info(f"✓ Backup file size: {backup_file.stat().st_size / (1024*1024):.2f} MB")
        logger.info("=" * 70)
            
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup working directory
        logger.info("Cleaning up temporary files...")
        try:
            shutil.rmtree(WORK_DIR)
        except:
            pass


if __name__ == "__main__":
    main()