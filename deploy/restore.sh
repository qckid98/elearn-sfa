#!/bin/bash
# =============================================================================
# Database Restore Script for elearn-sfa
# Usage: ./restore.sh <backup_file.sql.gz>
# =============================================================================

set -e

# Configuration
CONTAINER_NAME="elearn-sfa-db-1"
DB_NAME="${POSTGRES_DB:-fashion_db}"
DB_USER="${POSTGRES_USER:-postgres}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check arguments
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -la /var/www/elearn-sfa/backups/*/*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Verify file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Confirm restore
echo "⚠️  WARNING: This will REPLACE the current database with the backup!"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (type 'yes' to confirm): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

log "🗄️ Starting database restore..."

# Stop the web container to prevent connections
log "⏸️ Stopping web container..."
docker stop elearn-sfa-web-1 2>/dev/null || true

# Drop and recreate database
log "🔄 Recreating database..."
docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec ${CONTAINER_NAME} psql -U ${DB_USER} -c "CREATE DATABASE ${DB_NAME};"

# Restore from backup
log "📥 Restoring from backup..."
gunzip -c "${BACKUP_FILE}" | docker exec -i ${CONTAINER_NAME} psql -U ${DB_USER} ${DB_NAME}

# Start web container
log "▶️ Starting web container..."
docker start elearn-sfa-web-1

# Run migrations (in case backup is from older version)
log "🔄 Running migrations..."
sleep 5
docker exec elearn-sfa-web-1 flask db upgrade

log "✅ Database restore completed successfully!"
log "ℹ️ Please verify the application is working correctly."
