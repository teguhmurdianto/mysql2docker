#!/usr/bin/env python3
"""
mysql2docker - Backup MySQL database and bundle into Docker image
"""

import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_PORT = os.getenv('MYSQL_PORT', '3306')
MYSQL_USER = os.getenv('MYSQL_USER')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD')
MYSQL_DATABASE = os.getenv('MYSQL_DATABASE')

DOCKER_USERNAME = os.getenv('DOCKER_USERNAME')
DOCKER_IMAGE_NAME = os.getenv('DOCKER_IMAGE_NAME', 'mysql-backup')

BACKUP_DIR = Path('backups')
BACKUP_DIR.mkdir(exist_ok=True)


def validate_config():
    """Validate required environment variables"""
    required = {
        'MYSQL_USER': MYSQL_USER,
        'MYSQL_PASSWORD': MYSQL_PASSWORD,
        'MYSQL_DATABASE': MYSQL_DATABASE,
        'DOCKER_USERNAME': DOCKER_USERNAME
    }
    
    missing = [key for key, value in required.items() if not value]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please check your .env file")
        sys.exit(1)


def run_command(cmd, capture_output=False):
    """Execute shell command and handle errors"""
    try:
        logger.info(f"Running: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
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
        logger.error(f"Error output: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
        sys.exit(1)


def backup_mysql(timestamp):
    """Backup MySQL database with mysqldump"""
    backup_file = BACKUP_DIR / f"backup_{timestamp}.sql"
    backup_gz = BACKUP_DIR / f"backup_{timestamp}.sql.gz"
    
    logger.info(f"Starting MySQL backup for database: {MYSQL_DATABASE}")
    
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
        with open(backup_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=subprocess.PIPE, text=True)
        
        logger.info(f"Backup created: {backup_file}")
        
        # Compress with gzip
        logger.info("Compressing backup...")
        run_command(f"gzip {backup_file}")
        
        logger.info(f"Compressed backup: {backup_gz}")
        
        # Get file size
        size_mb = backup_gz.stat().st_size / (1024 * 1024)
        logger.info(f"Backup size: {size_mb:.2f} MB")
        
        return backup_gz
        
    except subprocess.CalledProcessError as e:
        logger.error(f"MySQL backup failed: {e.stderr if hasattr(e, 'stderr') else str(e)}")
        if backup_file.exists():
            backup_file.unlink()
        sys.exit(1)


def build_docker_image(timestamp):
    """Build Docker image containing the backup"""
    image_tag = f"{DOCKER_USERNAME}/{DOCKER_IMAGE_NAME}:backup_mysql_{timestamp}"
    
    logger.info(f"Building Docker image: {image_tag}")
    
    cmd = [
        'docker', 'build',
        '-t', image_tag,
        '.'
    ]
    
    run_command(cmd)
    logger.info(f"Docker image built successfully: {image_tag}")
    
    return image_tag


def push_docker_image(image_tag):
    """Push Docker image to DockerHub"""
    logger.info(f"Pushing image to DockerHub: {image_tag}")
    
    cmd = ['docker', 'push', image_tag]
    run_command(cmd)
    
    logger.info(f"Image pushed successfully: {image_tag}")


def main():
    """Main execution flow"""
    logger.info("=" * 60)
    logger.info("mysql2docker - MySQL Backup to Docker Image")
    logger.info("=" * 60)
    
    # Validate configuration
    validate_config()
    
    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Backup timestamp: {timestamp}")
    
    try:
        # Step 1: Backup MySQL
        backup_file = backup_mysql(timestamp)
        
        # Step 2: Build Docker image
        image_tag = build_docker_image(timestamp)
        
        # Step 3: Push to DockerHub
        push_docker_image(image_tag)
        
        logger.info("=" * 60)
        logger.info("✓ Backup process completed successfully!")
        logger.info(f"✓ Backup file: {backup_file}")
        logger.info(f"✓ Docker image: {image_tag}")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()