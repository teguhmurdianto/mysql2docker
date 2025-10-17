FROM python:3.11-alpine

LABEL maintainer="mysql2docker"
LABEL description="MySQL backup runner - creates Docker images from MySQL dumps"

# Install required packages
RUN apk add --no-cache \
    docker-cli \
    mariadb-client \
    gzip \
    ca-certificates

# Create working directory
WORKDIR /app

# Copy Python script
COPY backup_mysql.py /app/

# Make script executable
RUN chmod +x /app/backup_mysql.py

# Create temp directory for backups
RUN mkdir -p /tmp/mysql2docker

# Set entrypoint
ENTRYPOINT ["python", "/app/backup_mysql.py"]