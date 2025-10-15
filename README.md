# mysql2docker 🐬 → 🐳

Backup MySQL database and bundle it into a Docker image, then push to DockerHub as immutable backup snapshots.

## 💡 Concept

Unlike traditional backup solutions that store backups in S3, FTP, or local storage, `mysql2docker` uses **Docker images as the storage medium**. Each backup is bundled into a Docker image with a timestamp tag and pushed to your Docker registry.

**Benefits:**
- 📦 Immutable backup snapshots
- 🔐 Leverage existing Docker registry infrastructure
- 🏷️ Easy versioning with Docker tags
- 🚀 Simple restore process (pull image → extract backup)
- 💾 No additional storage service needed

## 📋 Prerequisites

- Python 3.6+
- MySQL client tools (`mysqldump`)
- Docker
- DockerHub account (or private Docker registry)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/mysql2docker.git
cd mysql2docker

# Install dependencies
pip install -r requirements.txt

# Create backups directory
mkdir -p backups
```

### 2. Configure

```bash
# Copy example config
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**.env Configuration:**
```bash
# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=your_mysql_user
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=your_database_name

# Docker Configuration
DOCKER_USERNAME=your_dockerhub_username
DOCKER_IMAGE_NAME=mysql-backup
```

### 3. Login to DockerHub

```bash
docker login
```

### 4. Run Backup

```bash
python backup_mysql.py
```

This will:
1. ✅ Backup MySQL database with `mysqldump`
2. ✅ Compress backup with gzip
3. ✅ Build Docker image with timestamp tag
4. ✅ Push image to DockerHub

**Example output:**
```
2024-10-16 10:30:45 - INFO - Starting MySQL backup for database: myapp
2024-10-16 10:30:48 - INFO - Compressed backup: backups/backup_20241016_103045.sql.gz
2024-10-16 10:30:48 - INFO - Backup size: 45.32 MB
2024-10-16 10:30:50 - INFO - Building Docker image: username/mysql-backup:backup_mysql_20241016_103045
2024-10-16 10:31:00 - INFO - Pushing image to DockerHub...
2024-10-16 10:31:25 - INFO - ✓ Backup process completed successfully!
```

## 📦 Restore Backup

### Option 1: Extract from Image

```bash
# Pull the backup image
docker pull username/mysql-backup:backup_mysql_20241016_103045

# Run container and copy backup file
docker run --rm -v $(pwd):/restore username/mysql-backup:backup_mysql_20241016_103045 sh -c "cp /backups/*.sql.gz /restore/"

# Decompress and restore
gunzip backup_20241016_103045.sql.gz
mysql -u username -p database_name < backup_20241016_103045.sql
```

### Option 2: Direct Restore

```bash
docker run --rm username/mysql-backup:backup_mysql_20241016_103045 cat /backups/backup_20241016_103045.sql.gz | \
gunzip | mysql -u username -p database_name
```

## 📁 Project Structure

```
mysql2docker/
├── backup_mysql.py      # Main backup script
├── Dockerfile           # Docker image definition
├── requirements.txt     # Python dependencies
├── .env.example         # Configuration template
├── .env                 # Your config (gitignored)
├── .dockerignore        # Docker build excludes
├── .gitignore          # Git excludes
├── backups/            # Local backup storage (gitignored)
├── LICENSE             # MIT License
└── README.md           # This file
```

## ⚙️ Advanced Usage

### Automated Backups with Cron

```bash
# Add to crontab
0 2 * * * cd /path/to/mysql2docker && /usr/bin/python3 backup_mysql.py >> /var/log/mysql2docker.log 2>&1
```

### Custom Backup Options

Edit `backup_mysql.py` and modify the `mysqldump` command to add options like:
- `--routines` - Include stored procedures
- `--triggers` - Include triggers
- `--events` - Include events
- `--skip-lock-tables` - For MyISAM tables

### Use Private Docker Registry

In `.env`, change:
```bash
DOCKER_USERNAME=registry.mycompany.com/backups
```

## 🔒 Security Notes

- ⚠️ Never commit `.env` file to git
- 🔐 Use strong MySQL passwords
- 🛡️ Use private Docker registry for production
- 🔑 Consider encrypting backups before bundling

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need for simple, reliable MySQL backups
- Built with ❤️ for the DevOps community

## 📞 Support

If you encounter any issues or have questions:
- 🐛 [Open an issue](https://github.com/yourusername/mysql2docker/issues)
- 💬 [Start a discussion](https://github.com/yourusername/mysql2docker/discussions)

---

**Made with 🐬 and 🐳**