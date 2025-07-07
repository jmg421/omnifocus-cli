#!/bin/bash
# Usage: ./ofcli_fresh.sh [--force] [ofcli.py arguments...]
# Only exports if the OmniFocus database has been modified since the last export.
# Use --force to override freshness check and always export.

set -e

# Parse command line arguments
FORCE_EXPORT=false
OFCLI_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_EXPORT=true
            shift
            ;;
        *)
            OFCLI_ARGS+=("$1")
            shift
            ;;
    esac
done

EXPORT_PATH="../data/omnifocus_export.json"
EXPORT_TIMESTAMP_PATH="../data/.omnifocus_export_timestamp"
BACKUP_DIR="../data/backups"
BACKUP_PATH="$BACKUP_DIR/omnifocus_export_backup.json"
BACKUP_TIMESTAMP_PATH="$BACKUP_DIR/.omnifocus_export_backup_timestamp"

# Possible OmniFocus database locations (in order of preference)
OMNIFOCUS_DB_PATHS=(
    "$HOME/Library/Containers/com.omnigroup.OmniFocus4/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus"
    "$HOME/Library/Containers/com.omnigroup.OmniFocus3/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus"
    "$HOME/Library/Containers/com.omnigroup.OmniFocus3.MacAppStore/Data/Library/Application Support/OmniFocus/OmniFocus.ofocus"
)

cd "$(dirname "$0")"
SCRIPT_DIR="$(pwd)"

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to create backup directory if it doesn't exist
ensure_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_message "Created backup directory: $BACKUP_DIR"
    fi
}

# Function to create pre-export backup
create_backup() {
    ensure_backup_dir
    
    if [ -f "$EXPORT_PATH" ]; then
        log_message "Creating backup of existing export..."
        cp "$EXPORT_PATH" "$BACKUP_PATH"
        
        # Also backup the timestamp if it exists
        if [ -f "$EXPORT_TIMESTAMP_PATH" ]; then
            cp "$EXPORT_TIMESTAMP_PATH" "$BACKUP_TIMESTAMP_PATH"
        fi
        
        log_message "Backup created successfully at: $BACKUP_PATH"
        return 0
    else
        log_message "No existing export to backup"
        return 1
    fi
}

# Function to verify export was successful
verify_export() {
    local export_file="$1"
    
    if [ ! -f "$export_file" ]; then
        log_message "ERROR: Export file not found: $export_file"
        return 1
    fi
    
    # Check if file is not empty
    if [ ! -s "$export_file" ]; then
        log_message "ERROR: Export file is empty: $export_file"
        return 1
    fi
    
    # Check if file is valid JSON
    if ! python3 -c "import json; json.load(open('$export_file')); print('valid')" >/dev/null 2>&1; then
        log_message "ERROR: Export file is not valid JSON: $export_file"
        return 1
    fi
    
    # Check if JSON has expected structure (tasks, projects, etc.)
    local has_structure=$(python3 -c "
import json
import sys
try:
    with open('$export_file') as f:
        data = json.load(f)
    # Check for expected keys that indicate a valid OmniFocus export
    if isinstance(data, dict) and ('tasks' in data or 'projects' in data or 'exportDate' in data):
        print('true')
    else:
        print('false')
except:
    print('false')
" 2>/dev/null)
    
    if [ "$has_structure" != "true" ]; then
        log_message "ERROR: Export file does not have expected OmniFocus structure"
        return 1
    fi
    
    log_message "Export verification successful"
    return 0
}

# Function to restore from backup
restore_from_backup() {
    if [ -f "$BACKUP_PATH" ]; then
        log_message "Restoring from backup..."
        cp "$BACKUP_PATH" "$EXPORT_PATH"
        
        # Also restore the timestamp if it exists
        if [ -f "$BACKUP_TIMESTAMP_PATH" ]; then
            cp "$BACKUP_TIMESTAMP_PATH" "$EXPORT_TIMESTAMP_PATH"
        fi
        
        log_message "Backup restored successfully"
        return 0
    else
        log_message "WARNING: No backup available to restore"
        return 1
    fi
}

# Function to commit successful export
commit_export() {
    local db_path="$1"
    
    # Record the export timestamp
    echo $(date +%s) > "$EXPORT_TIMESTAMP_PATH"
    
    # Create a success log entry
    local success_msg="Export completed successfully at $(date '+%Y-%m-%d %H:%M:%S')"
    log_message "$success_msg"
    
    # Optionally clean up old backups (keep last 5)
    cleanup_old_backups
    
    log_message "Export committed and timestamp recorded"
}

# Function to cleanup old backups
cleanup_old_backups() {
    if [ -d "$BACKUP_DIR" ]; then
        # Create timestamped backup names for historical backups
        local timestamp=$(date '+%Y%m%d_%H%M%S')
        local historical_backup="$BACKUP_DIR/omnifocus_export_backup_$timestamp.json"
        
        # Move current backup to historical name
        if [ -f "$BACKUP_PATH" ]; then
            mv "$BACKUP_PATH" "$historical_backup"
        fi
        
        # Keep only the last 5 historical backups
        local backup_count=$(ls -1 "$BACKUP_DIR"/omnifocus_export_backup_*.json 2>/dev/null | wc -l)
        if [ "$backup_count" -gt 5 ]; then
            ls -1t "$BACKUP_DIR"/omnifocus_export_backup_*.json | tail -n +6 | xargs rm -f
            log_message "Cleaned up old backups (kept last 5)"
        fi
    fi
}

# Function to find the active OmniFocus database
find_omnifocus_database() {
    for db_path in "${OMNIFOCUS_DB_PATHS[@]}"; do
        if [ -e "$db_path" ]; then
            echo "$db_path"
            return 0
        fi
    done
    return 1
}

# Function to get the modification time of the database bundle
get_db_mtime() {
    local db_path="$1"
    # Get the most recent modification time within the database bundle
    # The .ofocus file is actually a bundle/directory containing multiple files
    find "$db_path" -type f -exec stat -f "%m" {} \; 2>/dev/null | sort -nr | head -1
}

# Function to check if export is needed
needs_export() {
    local db_path="$1"
    
    # Always export if force flag is set
    if [ "$FORCE_EXPORT" = true ]; then
        echo "Force export requested"
        return 0
    fi
    
    # Always export if export file doesn't exist
    if [ ! -f "$EXPORT_PATH" ]; then
        echo "Export file doesn't exist"
        return 0
    fi
    
    # Always export if timestamp file doesn't exist
    if [ ! -f "$EXPORT_TIMESTAMP_PATH" ]; then
        echo "Timestamp file doesn't exist"
        return 0
    fi
    
    # Get database modification time
    local db_mtime=$(get_db_mtime "$db_path")
    if [ -z "$db_mtime" ]; then
        echo "Could not get database modification time"
        return 0
    fi
    
    # Get last export timestamp
    local last_export_time=$(cat "$EXPORT_TIMESTAMP_PATH" 2>/dev/null || echo "0")
    
    # Compare timestamps
    if [ "$db_mtime" -gt "$last_export_time" ]; then
        echo "Database modified since last export (DB: $db_mtime, Export: $last_export_time)"
        return 0
    else
        echo "Database unchanged since last export"
        return 1
    fi
}

# Function to perform the actual export with backup and restore
perform_export() {
    local db_path="$1"
    local export_method="$2"
    
    log_message "Starting export process with backup protection..."
    
    # Create backup before export
    create_backup
    local backup_created=$?
    
    # Perform the export
    export_success=false
    export_error=""
    
    case "$export_method" in
        "omnifocus-mcp")
            log_message "Exporting via OmniFocus-MCP..."
            cd ../OmniFocus-MCP
            if npx ts-node src/dumpDatabaseCli.ts >/dev/null 2>&1; then
                export_success=true
            else
                export_error="OmniFocus-MCP export failed"
            fi
            cd "$SCRIPT_DIR"
            ;;
        "fallback")
            log_message "Exporting via fallback method..."
            cd ../OmniFocus-MCP
            if npx ts-node src/dumpDatabaseCli.ts >/dev/null 2>&1; then
                export_success=true
            else
                export_error="Fallback export failed"
            fi
            cd "$SCRIPT_DIR"
            ;;
    esac
    
    # Verify the export
    if [ "$export_success" = true ]; then
        if verify_export "$EXPORT_PATH"; then
            log_message "Export successful and verified"
            commit_export "$db_path"
            return 0
        else
            export_error="Export verification failed"
            export_success=false
        fi
    fi
    
    # Handle export failure
    if [ "$export_success" = false ]; then
        log_message "ERROR: $export_error"
        
        if [ $backup_created -eq 0 ]; then
            log_message "Attempting to restore from backup..."
            if restore_from_backup; then
                log_message "Backup restored successfully. Using previous export."
                return 1  # Return error code but system is stable
            else
                log_message "CRITICAL: Export failed and backup restore failed"
                return 2  # Critical error
            fi
        else
            log_message "CRITICAL: Export failed and no backup was available"
            return 2  # Critical error
        fi
    fi
}

# Main execution logic
log_message "Starting OmniFocus export freshness check..."

# Find the active OmniFocus database
OMNIFOCUS_DB_PATH=$(find_omnifocus_database)

if [ -z "$OMNIFOCUS_DB_PATH" ]; then
    log_message "Warning: Could not find OmniFocus database. Falling back to time-based export."
    # Fallback to original time-based logic
    EXPORT_MAX_AGE=3600  # seconds (1 hour)
    if [ "$FORCE_EXPORT" = true ] || [ ! -f "$EXPORT_PATH" ] || [ $(( $(date +%s) - $(stat -f %m "$EXPORT_PATH") )) -gt $EXPORT_MAX_AGE ]; then
        perform_export "" "fallback"
        export_result=$?
        if [ $export_result -eq 2 ]; then
            log_message "CRITICAL: Export failed completely"
            exit 1
        fi
    else
        log_message "Using existing export: $EXPORT_PATH"
    fi
else
    log_message "Found OmniFocus database at: $OMNIFOCUS_DB_PATH"
    
    # Check if export is needed based on database freshness
    if needs_export "$OMNIFOCUS_DB_PATH"; then
        perform_export "$OMNIFOCUS_DB_PATH" "omnifocus-mcp"
        export_result=$?
        if [ $export_result -eq 2 ]; then
            log_message "CRITICAL: Export failed completely"
            exit 1
        fi
    else
        log_message "Using existing export: $EXPORT_PATH"
    fi
fi

# Run the requested ofcli.py command with fresh data
log_message "Running ofcli.py with verified export data..."
cd "$SCRIPT_DIR"
python3 ofcli.py "${OFCLI_ARGS[@]}"