#!/bin/bash
# =============================================================================
# PostgreSQL Backup Script for elearn-sfa
# Supports: Local backup, rotation, and Google Drive upload
# =============================================================================

set -e

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BACKUP_DIR="/var/www/elearn-sfa/backups"
CONTAINER_NAME="elearn-sfa-db-1"  # Docker container name
DB_NAME="${POSTGRES_DB:-fashion_db}"
DB_USER="${POSTGRES_USER:-postgres}"

# Google Drive settings (using rclone)
GDRIVE_REMOTE="gdrive"  # rclone remote name (configured via 'rclone config')
GDRIVE_FOLDER="elearn-sfa-backups"  # Folder name in Google Drive

# Retention settings
KEEP_DAILY=7       # Keep 7 daily backups
KEEP_WEEKLY=4      # Keep 4 weekly backups
KEEP_MONTHLY=3     # Keep 3 monthly backups

# Timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DAY_OF_WEEK=$(date +%u)  # 1=Monday, 7=Sunday
DAY_OF_MONTH=$(date +%d)

# Backup filename
if [ "$DAY_OF_MONTH" == "01" ]; then
    BACKUP_TYPE="monthly"
elif [ "$DAY_OF_WEEK" == "7" ]; then
    BACKUP_TYPE="weekly"
else
    BACKUP_TYPE="daily"
fi

BACKUP_FILE="${BACKUP_DIR}/${BACKUP_TYPE}/backup_${TIMESTAMP}.sql.gz"

# -----------------------------------------------------------------------------
# Functions
# -----------------------------------------------------------------------------

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

create_backup() {
    log "🗄️ Starting ${BACKUP_TYPE} backup..."
    
    # Create backup directories
    mkdir -p "${BACKUP_DIR}/daily"
    mkdir -p "${BACKUP_DIR}/weekly"
    mkdir -p "${BACKUP_DIR}/monthly"
    
    # Perform backup using docker exec
    docker exec ${CONTAINER_NAME} pg_dump -U ${DB_USER} ${DB_NAME} | gzip > "${BACKUP_FILE}"
    
    # Get file size
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log "✅ Backup completed: ${BACKUP_FILE} (${SIZE})"
}

rotate_backups() {
    log "🔄 Rotating old backups..."
    
    # Rotate daily backups (keep last 7)
    cd "${BACKUP_DIR}/daily"
    ls -t backup_*.sql.gz 2>/dev/null | tail -n +$((KEEP_DAILY + 1)) | xargs -r rm -f
    
    # Rotate weekly backups (keep last 4)
    cd "${BACKUP_DIR}/weekly"
    ls -t backup_*.sql.gz 2>/dev/null | tail -n +$((KEEP_WEEKLY + 1)) | xargs -r rm -f
    
    # Rotate monthly backups (keep last 3)
    cd "${BACKUP_DIR}/monthly"
    ls -t backup_*.sql.gz 2>/dev/null | tail -n +$((KEEP_MONTHLY + 1)) | xargs -r rm -f
    
    log "✅ Local rotation completed"
}

upload_to_gdrive() {
    log "☁️ Uploading to Google Drive..."
    
    # Check if rclone is installed
    if ! command -v rclone &> /dev/null; then
        log "❌ rclone not installed. Run: curl https://rclone.org/install.sh | sudo bash"
        return 1
    fi
    
    # Check if remote is configured
    if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:"; then
        log "❌ rclone remote '${GDRIVE_REMOTE}' not configured. Run: rclone config"
        return 1
    fi
    
    # Create folder structure in Google Drive
    rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${BACKUP_TYPE}" 2>/dev/null || true
    
    # Upload backup file
    rclone copy "${BACKUP_FILE}" "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${BACKUP_TYPE}/" \
        --progress \
        --log-level INFO
    
    log "✅ Uploaded to Google Drive: ${GDRIVE_FOLDER}/${BACKUP_TYPE}/$(basename ${BACKUP_FILE})"
    
    # Rotate old backups in Google Drive
    rotate_gdrive_backups
}

rotate_gdrive_backups() {
    log "🔄 Rotating old backups in Google Drive..."
    
    # Get list of files in each folder and delete old ones
    for TYPE in daily weekly monthly; do
        case $TYPE in
            daily)   KEEP=$KEEP_DAILY ;;
            weekly)  KEEP=$KEEP_WEEKLY ;;
            monthly) KEEP=$KEEP_MONTHLY ;;
        esac
        
        # List files, sort by name (which includes timestamp), and delete old ones
        FILES=$(rclone lsf "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${TYPE}/" 2>/dev/null | sort -r)
        COUNT=0
        
        for FILE in $FILES; do
            COUNT=$((COUNT + 1))
            if [ $COUNT -gt $KEEP ]; then
                log "  Deleting old backup: ${TYPE}/${FILE}"
                rclone delete "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${TYPE}/${FILE}"
            fi
        done
    done
    
    log "✅ Google Drive rotation completed"
}

verify_backup() {
    log "🔍 Verifying backup integrity..."
    
    if gzip -t "${BACKUP_FILE}" 2>/dev/null; then
        log "✅ Backup file is valid"
    else
        log "❌ Backup file is corrupted!"
        exit 1
    fi
}

show_status() {
    log "📊 Backup Status:"
    echo ""
    echo "=== LOCAL BACKUPS ==="
    echo ""
    echo "Daily backups (keeping ${KEEP_DAILY}):"
    ls -lh "${BACKUP_DIR}/daily/" 2>/dev/null | tail -5 || echo "  No daily backups"
    echo ""
    echo "Weekly backups (keeping ${KEEP_WEEKLY}):"
    ls -lh "${BACKUP_DIR}/weekly/" 2>/dev/null | tail -5 || echo "  No weekly backups"
    echo ""
    echo "Monthly backups (keeping ${KEEP_MONTHLY}):"
    ls -lh "${BACKUP_DIR}/monthly/" 2>/dev/null | tail -5 || echo "  No monthly backups"
    echo ""
    echo "Total local backup size:"
    du -sh "${BACKUP_DIR}" 2>/dev/null || echo "  No backups yet"
    
    # Show Google Drive status if rclone is configured
    if command -v rclone &> /dev/null && rclone listremotes | grep -q "^${GDRIVE_REMOTE}:"; then
        echo ""
        echo "=== GOOGLE DRIVE BACKUPS ==="
        echo ""
        for TYPE in daily weekly monthly; do
            echo "${TYPE^} backups:"
            rclone lsl "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/${TYPE}/" 2>/dev/null | tail -5 || echo "  No ${TYPE} backups"
            echo ""
        done
        
        echo "Total Google Drive backup size:"
        rclone size "${GDRIVE_REMOTE}:${GDRIVE_FOLDER}/" 2>/dev/null || echo "  Could not calculate"
    fi
}

setup_rclone() {
    log "🔧 Setting up rclone for Google Drive..."
    
    # Install rclone if not present
    if ! command -v rclone &> /dev/null; then
        log "Installing rclone..."
        curl https://rclone.org/install.sh | sudo bash
    fi
    
    echo ""
    echo "=============================================="
    echo "  RCLONE GOOGLE DRIVE SETUP"
    echo "=============================================="
    echo ""
    echo "Run the following command to configure Google Drive:"
    echo ""
    echo "  rclone config"
    echo ""
    echo "Then follow these steps:"
    echo "  1. Type 'n' for new remote"
    echo "  2. Name: gdrive"
    echo "  3. Storage: Choose 'Google Drive' (usually number 15)"
    echo "  4. Client ID: (press Enter for default, or use your own)"
    echo "  5. Client Secret: (press Enter for default)"
    echo "  6. Scope: Choose '1' (full access)"
    echo "  7. Root folder ID: (press Enter for root)"
    echo "  8. Service Account: (press Enter for none)"
    echo "  9. Advanced config: 'n'"
    echo "  10. Auto config: 'n' (for headless server)"
    echo "  11. Follow the URL to authorize"
    echo "  12. Paste the verification code"
    echo "  13. Team Drive: 'n'"
    echo "  14. Confirm with 'y'"
    echo ""
    echo "After setup, test with:"
    echo "  rclone lsd gdrive:"
    echo ""
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

case "${1:-backup}" in
    backup)
        create_backup
        verify_backup
        rotate_backups
        upload_to_gdrive
        log "🎉 Backup process completed successfully!"
        ;;
    backup-local)
        create_backup
        verify_backup
        rotate_backups
        log "🎉 Local backup completed (no cloud upload)"
        ;;
    status)
        show_status
        ;;
    setup)
        setup_rclone
        ;;
    upload)
        # Upload existing backup to cloud
        if [ -z "$2" ]; then
            log "Usage: $0 upload <backup_file>"
            exit 1
        fi
        BACKUP_FILE="$2"
        BACKUP_TYPE=$(dirname "$2" | xargs basename)
        upload_to_gdrive
        ;;
    *)
        echo "Usage: $0 {backup|backup-local|status|setup|upload <file>}"
        echo ""
        echo "Commands:"
        echo "  backup       - Create backup and upload to Google Drive"
        echo "  backup-local - Create backup locally only"
        echo "  status       - Show backup status (local and cloud)"
        echo "  setup        - Setup rclone for Google Drive"
        echo "  upload       - Upload specific backup file to cloud"
        exit 1
        ;;
esac
