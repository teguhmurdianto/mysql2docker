# mysql2docker 🐬 → 🐳

Backup MySQL database and bundle it into a Docker image, then push to DockerHub as immutable backup snapshots.

**Now with Docker-in-Docker support!** Run backups from any Docker environment without installing dependencies on your host.

## 💡 Concept

Unlike traditional backup solutions that store backups in S3, FTP, or local storage, `mysql2docker` uses **Docker images as the storage medium**. Each backup is bundled into a Docker image with a timestamp tag and pushed to your Docker registry.

**Architecture:**
```
┌─────────────────────────────────────┐
│  mysql2docker:latest (Runner)       │
│  - Python script                    │
│  - Docker CLI                       │
│  - MySQL client (mysqldump)         │
└─────────────────────────────────────┘
         │ (mounts /var/run/docker.sock)
         ▼
  ┌──────────────────────┐
  │  Backup Process:     │
  │  1. mysqldump        │
  │  2. gzip compress    │
  │  3. Build dump image │
  │  4. Push to registry │
  └──────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│  username/mysql-backup:timestamp    │
│  - Alpine minimal                   │
│  - Only backup .sql.gz file         │
└─────────────────────────────────────┘
```

**Benefits:**
- 📦 Immutable backup snapshots
- 🔐 Leverage existing Docker registry infrastructure
- 🏷️ Easy versioning with Docker tags
- 🚀 Simple restore process (pull image → extract backup)
- 💾 No additional storage service needed
- 🐳 Works on any Docker environment (Linux, macOS, Windows WSL, K8s, CI/CD)
- 🔧 No host dependencies - everything runs in containers

## 📋 Prerequisites

- Docker installed
- Docker registry account (DockerHub or private registry)
- MySQL database accessible from Docker network

**That's it!** No need to install Python, mysqldump, or any other tools on your host.

### 🔌 Network Considerations

If your MySQL server has **IP whitelist enabled**, you have two options:

**Option 1: Host Network Mode (Recommended for IP Whitelist)**
```bash
# Container uses host IP directly
docker run --rm \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MYSQL_HOST=localhost \
  mysql2docker:latest
```
- ✅ Works with MySQL IP whitelist (uses host IP)
- ✅ Perfect for production servers
- ⚠️ Only works on Linux (not Docker Desktop macOS/Windows)

**Option 2: Bridge Network (Default)**
```bash
# Container uses Docker bridge network IP
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MYSQL_HOST=mysql-server \
  mysql2docker:latest
```
- ✅ Works on all platforms
- ⚠️ Requires whitelisting Docker bridge IP range (e.g., 172.17.0.0/16)

## 🚀 Quick Start

### Option 1: Use Pre-built Image (Recommended)

#### For MySQL with IP Whitelist (Host Network)

```bash
# Pull the runner image
docker pull mysql2docker/mysql2docker:latest

# Run backup using host network (Linux only)
docker run --rm \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MYSQL_HOST=localhost \
  -e MYSQL_PORT=3306 \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=your_password \
  -e MYSQL_DATABASE=your_database \
  -e DOCKER_USERNAME=your_dockerhub_username \
  -e DOCKER_PASSWORD=your_dockerhub_token \
  -e DOCKER_IMAGE_NAME=mysql-backup \
  mysql2docker/mysql2docker:latest
```

#### For MySQL Without IP Whitelist (Bridge Network)

```bash
# Run backup using bridge network
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MYSQL_HOST=your-mysql-host \
  -e MYSQL_PORT=3306 \
  -e MYSQL_USER=root \
  -e MYSQL_PASSWORD=your_password \
  -e MYSQL_DATABASE=your_database \
  -e DOCKER_USERNAME=your_dockerhub_username \
  -e DOCKER_PASSWORD=your_dockerhub_token \
  -e DOCKER_IMAGE_NAME=mysql-backup \
  mysql2docker/mysql2docker:latest
```

### Option 2: Build from Source

```bash
# Clone repository
git clone https://github.com/yourusername/mysql2docker.git
cd mysql2docker

# Build runner image
docker build -t mysql2docker:latest .

# Run backup
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file .env \
  mysql2docker:latest
```

## 📝 Configuration

### Environment Variables

Create a `.env` file:

```bash
# MySQL Configuration
MYSQL_HOST=db.example.com
MYSQL_PORT=3306
MYSQL_USER=backup_user
MYSQL_PASSWORD=secure_password
MYSQL_DATABASE=production_db

# Docker Registry
DOCKER_USERNAME=yourname
DOCKER_PASSWORD=dckr_pat_xxxxxxxxxxxxx  # Use access token!
DOCKER_IMAGE_NAME=mysql-backup

# Optional: Custom tag (default: auto timestamp)
# CUSTOM_TAG=production-v1
```

### Using with docker-compose

**Example 1: MySQL with IP Whitelist (Host Network)**

```yaml
version: '3.8'

services:
  mysql-backup-host:
    image: mysql2docker/mysql2docker:latest
    network_mode: host  # Uses host IP
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - MYSQL_HOST=localhost  # or actual MySQL server IP
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=myapp
      - DOCKER_USERNAME=${DOCKER_USERNAME}
      - DOCKER_PASSWORD=${DOCKER_PASSWORD}
      - DOCKER_IMAGE_NAME=mysql-backup
```

Run with:
```bash
docker-compose run --rm mysql-backup-host
```

**Example 2: MySQL Without IP Whitelist (Bridge Network)**

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: myapp
    networks:
      - backup-network

  mysql-backup-bridge:
    image: mysql2docker/mysql2docker:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - MYSQL_HOST=mysql  # service name
      - MYSQL_PORT=3306
      - MYSQL_USER=root
      - MYSQL_PASSWORD=${MYSQL_ROOT_PASSWORD}
      - MYSQL_DATABASE=myapp
      - DOCKER_USERNAME=${DOCKER_USERNAME}
      - DOCKER_PASSWORD=${DOCKER_PASSWORD}
      - DOCKER_IMAGE_NAME=mysql-backup
    networks:
      - backup-network
    depends_on:
      - mysql

networks:
  backup-network:
```

Run with:
```bash
docker-compose run --rm mysql-backup-bridge
```

## 📦 Restore Backup

### Option 1: Extract Backup File

```bash
# Pull the backup image
docker pull username/mysql-backup:backup_mysql_20241016_103045

# Extract backup file to current directory
docker run --rm \
  -v $(pwd):/restore \
  username/mysql-backup:backup_mysql_20241016_103045 \
  sh -c "cp /backups/*.sql.gz /restore/"

# Decompress and restore
gunzip backup_20241016_103045.sql.gz
mysql -h your-host -u root -p your_database < backup_20241016_103045.sql
```

### Option 2: Direct Restore (One Command)

```bash
# Stream backup directly to MySQL
docker run --rm username/mysql-backup:backup_mysql_20241016_103045 \
  sh -c "cat /backups/*.sql.gz" | \
  gunzip | \
  mysql -h your-host -u root -p your_database
```

### Option 3: Restore in Docker Network

```bash
# If MySQL is in Docker network
docker run --rm --network your_network \
  username/mysql-backup:backup_mysql_20241016_103045 \
  sh -c "cat /backups/*.sql.gz" | \
  gunzip | \
  docker exec -i mysql_container mysql -u root -p your_database
```

## 🔄 Automated Backups

### Using Cron (Linux/macOS)

**With Host Network (for IP Whitelist):**
```bash
# Add to crontab: backup daily at 2 AM
0 2 * * * docker run --rm --network host -v /var/run/docker.sock:/var/run/docker.sock --env-file /path/to/.env mysql2docker:latest >> /var/log/mysql2docker.log 2>&1
```

**With Bridge Network:**
```bash
0 2 * * * docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --env-file /path/to/.env mysql2docker:latest >> /var/log/mysql2docker.log 2>&1
```

### Using systemd Timer (Linux)

Create `/etc/systemd/system/mysql-backup.service`:

**With Host Network:**
```ini
[Unit]
Description=MySQL Backup to Docker

[Service]
Type=oneshot
ExecStart=/usr/bin/docker run --rm \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file /etc/mysql2docker/.env \
  mysql2docker:latest
```

**With Bridge Network:**
```ini
[Unit]
Description=MySQL Backup to Docker

[Service]
Type=oneshot
ExecStart=/usr/bin/docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file /etc/mysql2docker/.env \
  mysql2docker:latest
```

Create `/etc/systemd/system/mysql-backup.timer`:

```ini
[Unit]
Description=Daily MySQL Backup

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl enable mysql-backup.timer
sudo systemctl start mysql-backup.timer
```

### Using Kubernetes CronJob

**With Host Network (for IP Whitelist):**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mysql-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          hostNetwork: true  # Use host network
          containers:
          - name: mysql-backup
            image: mysql2docker/mysql2docker:latest
            env:
            - name: MYSQL_HOST
              value: "localhost"  # or MySQL server IP
            - name: MYSQL_USER
              valueFrom:
                secretKeyRef:
                  name: mysql-credentials
                  key: username
            - name: MYSQL_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: mysql-credentials
                  key: password
            - name: MYSQL_DATABASE
              value: "myapp"
            - name: DOCKER_USERNAME
              valueFrom:
                secretKeyRef:
                  name: docker-credentials
                  key: username
            - name: DOCKER_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: docker-credentials
                  key: password
            - name: DOCKER_IMAGE_NAME
              value: "mysql-backup"
            volumeMounts:
            - name: docker-sock
              mountPath: /var/run/docker.sock
          volumes:
          - name: docker-sock
            hostPath:
              path: /var/run/docker.sock
          restartPolicy: OnFailure
```

**With Bridge Network:**
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: mysql-backup
spec:
  schedule: "0 2 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: mysql-backup
            image: mysql2docker/mysql2docker:latest
            env:
            - name: MYSQL_HOST
              value: "mysql-service"  # K8s service name
            # ... other env vars same as above
            volumeMounts:
            - name: docker-sock
              mountPath: /var/run/docker.sock
          volumes:
          - name: docker-sock
            hostPath:
              path: /var/run/docker.sock
          restartPolicy: OnFailure
```

## 📁 Project Structure

```
mysql2docker/
├── Dockerfile              # Runner image definition
├── backup_mysql.py         # Main backup script
├── .env.example            # Configuration template
├── .dockerignore           # Docker build excludes
├── .gitignore              # Git excludes
├── docker-compose.yml      # Example compose file
├── LICENSE                 # MIT License
└── README.md               # This file
```

## ⚙️ Advanced Usage

### MySQL IP Whitelist Configuration

If your MySQL server has IP whitelist enabled, here are your options:

**1. Host Network Mode (Recommended for Linux)**
```bash
docker run --rm \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e MYSQL_HOST=localhost \
  mysql2docker:latest
```
- Container uses host IP
- Works only on Linux
- MySQL sees connection from whitelisted host IP

**2. Whitelist Docker Bridge Network**
```bash
# Find Docker bridge subnet
docker network inspect bridge | grep Subnet
# Example output: "Subnet": "172.17.0.0/16"

# Add to MySQL whitelist
# In MySQL: GRANT ALL ON *.* TO 'user'@'172.17.0.%' IDENTIFIED BY 'password';
```

**3. Custom Docker Network with Static IP**
```bash
# Create network with specific subnet
docker network create --subnet=192.168.100.0/24 backup-net

# Run container with static IP
docker run --rm \
  --network backup-net \
  --ip 192.168.100.10 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  mysql2docker:latest

# Whitelist 192.168.100.10 in MySQL
```

### Custom Backup Tag

```bash
# Use custom tag instead of timestamp
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e CUSTOM_TAG=production-backup-v2 \
  --env-file .env \
  mysql2docker:latest
```

### Backup to Private Registry

```bash
# Use private Docker registry
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DOCKER_USERNAME=registry.mycompany.com/backups \
  -e DOCKER_PASSWORD=token \
  --env-file .env \
  mysql2docker:latest
```

### Network Configuration

If MySQL is in a Docker network:

```bash
docker run --rm \
  --network your_mysql_network \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --env-file .env \
  mysql2docker:latest
```

### Custom mysqldump Options

Edit `backup_mysql.py` to add options:
- `--routines` - Include stored procedures
- `--triggers` - Include triggers
- `--events` - Include scheduled events
- `--master-data` - For replication setup

## 🔒 Security Best Practices

### 1. Use Docker Access Tokens

For DockerHub, create an access token instead of using your password:
1. Go to https://hub.docker.com/settings/security
2. Create new access token
3. Use token as `DOCKER_PASSWORD`

### 2. Protect Environment Variables

```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Set proper file permissions
chmod 600 .env
```

### 3. Use Docker Secrets (Swarm/K8s)

```bash
# Create secrets
echo "mypassword" | docker secret create mysql_password -
echo "dockertoken" | docker secret create docker_token -

# Use in service
docker service create \
  --secret mysql_password \
  --secret docker_token \
  mysql2docker:latest
```

### 4. Network Isolation

```bash
# Create dedicated backup network
docker network create backup-network

# Run backup in isolated network
docker run --rm \
  --network backup-network \
  -v /var/run/docker.sock:/var/run/docker.sock \
  mysql2docker:latest
```

### 5. Encrypt Backups

Consider encrypting backups before pushing:

```bash
# In backup_mysql.py, add encryption step:
# openssl enc -aes-256-cbc -salt -in backup.sql.gz -out backup.sql.gz.enc -k $ENCRYPTION_KEY
```

## 🐛 Troubleshooting

### Error: "Cannot connect to the Docker daemon"

**Solution:** Ensure Docker socket is mounted correctly:
```bash
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  mysql2docker:latest
```

### Error: "Access denied for user" or Connection Timeout

The backup script will automatically test the MySQL connection before starting the backup.

**Common causes:**

1. **IP Whitelist Issue** (Most Common)
   ```
   Error: Host 'xxx.xxx.xxx.xxx' is not allowed to connect
   ```
   **Solution:** Use host network mode:
   ```bash
   docker run --rm \
     --network host \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -e MYSQL_HOST=localhost \
     mysql2docker:latest
   ```

2. **Wrong Credentials**
   ```
   Error: Access denied for user 'root'@'localhost'
   ```
   **Solution:** Verify credentials:
   ```bash
   # Test connection manually
   docker run --rm mysql:8 mysql \
     -h $MYSQL_HOST \
     -u $MYSQL_USER \
     -p$MYSQL_PASSWORD \
     -e "SELECT 1"
   ```

3. **Database Not Exists**
   ```
   Error: Unknown database 'mydb'
   ```
   **Solution:** Check database name:
   ```bash
   docker run --rm mysql:8 mysql \
     -h $MYSQL_HOST \
     -u $MYSQL_USER \
     -p$MYSQL_PASSWORD \
     -e "SHOW DATABASES"
   ```

4. **Firewall/Network Issue**
   ```
   Error: Can't connect to MySQL server on 'host'
   ```
   **Solution:** Check network connectivity:
   ```bash
   # Test from container
   docker run --rm alpine ping -c 3 $MYSQL_HOST
   
   # Test port
   docker run --rm alpine nc -zv $MYSQL_HOST 3306
   ```

### Connection Test Output

The script will show detailed connection test results:

```
2024-10-16 10:30:00 - INFO - Testing MySQL connection...
2024-10-16 10:30:00 - INFO - Connecting to: db.example.com:3306
2024-10-16 10:30:01 - INFO - ✓ MySQL connection successful!
```

If connection fails:
```
2024-10-16 10:30:00 - INFO - Testing MySQL connection...
2024-10-16 10:30:00 - INFO - Connecting to: db.example.com:3306
2024-10-16 10:30:10 - ERROR - ✗ MySQL connection failed!
2024-10-16 10:30:10 - ERROR - Please check:
2024-10-16 10:30:10 - ERROR -   1. MySQL credentials (user/password)
2024-10-16 10:30:10 - ERROR -   2. Database name is correct
2024-10-16 10:30:10 - ERROR -   3. User has proper permissions
2024-10-16 10:30:10 - ERROR -   4. IP whitelist (if using Docker, consider --network host)
```

### Error: "unauthorized: authentication required"

**Solution:** Login to Docker registry first or check credentials:
```bash
docker login
# Or use token in DOCKER_PASSWORD
```

### Windows WSL Issues

If using Windows with WSL2:
```bash
# Use WSL2 Docker socket path
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  mysql2docker:latest
```

**Note:** Host network mode (`--network host`) does NOT work on Docker Desktop (Windows/macOS). If you need to connect to MySQL with IP whitelist on these platforms:

1. **Option A:** Add Docker Desktop VM IP to MySQL whitelist
2. **Option B:** Use SSH tunnel:
   ```bash
   # Forward MySQL port via SSH
   ssh -L 3306:localhost:3306 user@mysql-server
   
   # Then connect to localhost from container
   ```
3. **Option C:** Run on Linux server where host network works

## 📊 Monitoring and Logging

### View Backup Logs

```bash
# If running as daemon
docker logs -f container_name

# With cron, check system logs
tail -f /var/log/mysql2docker.log
```

### List Available Backups

```bash
# List all backup images
docker images | grep mysql-backup

# Or search in registry
curl -s https://hub.docker.com/v2/repositories/$USERNAME/mysql-backup/tags/ | jq
```

### Verify Backup Integrity

```bash
# Run backup image to see info
docker run --rm username/mysql-backup:backup_mysql_20241016_103045
```

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Support for PostgreSQL
- [ ] Incremental backups
- [ ] Backup encryption
- [ ] Notification support (Slack, email)
- [ ] Backup rotation/cleanup
- [ ] Web UI for management
- [ ] Metrics and monitoring

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/mysql2docker.git
cd mysql2docker

# Build local image
docker build -t mysql2docker:dev .

# Test
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock --env-file .env mysql2docker:dev
```

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by the need for simple, reliable MySQL backups
- Built with ❤️ for the DevOps community
- Thanks to all contributors

## 📞 Support

- 🐛 [Report Issues](https://github.com/yourusername/mysql2docker/issues)
- 💬 [Discussions](https://github.com/yourusername/mysql2docker/discussions)
- 📧 Email: support@mysql2docker.io

## 🌟 Show Your Support

If this project helped you, please:
- ⭐ Star this repository
- 🐦 Share on Twitter
- 📝 Write a blog post
- 💰 Sponsor the project

---

**Made with 🐬 and 🐳 by the mysql2docker community**