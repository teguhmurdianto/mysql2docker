FROM alpine:latest

LABEL maintainer="mysql2docker"
LABEL description="MySQL backup bundled in Docker image"

# Create backup directory
RUN mkdir -p /backups

# Copy all backup files
COPY backups/*.sql.gz /backups/

# Add metadata
RUN echo "Backup created at: $(date)" > /backups/backup_info.txt

# Default command to list backups
CMD ["sh", "-c", "ls -lh /backups && cat /backups/backup_info.txt"]