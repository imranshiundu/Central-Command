#!/bin/bash
# MEGA Cloud Controller Script

COMMAND="$1"
FILE_PATH="$2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/mega_controller.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if MEGAcmd is installed
if ! command -v mega-put >/dev/null 2>&1; then
    echo "ERROR: MEGAcmd not installed. Install with: sudo apt-get install megacmd"
    log_message "ERROR: MEGAcmd not installed"
    exit 1
fi

case "$COMMAND" in
    "upload")
        if [ -z "$FILE_PATH" ]; then
            echo "ERROR: File path required"
            exit 1
        fi
        
        if [ ! -f "$FILE_PATH" ] && [ ! -d "$FILE_PATH" ]; then
            echo "ERROR: File not found: $FILE_PATH"
            exit 1
        fi
        
        log_message "Uploading: $FILE_PATH"
        mega-put "$FILE_PATH" "/"
        if [ $? -eq 0 ]; then
            echo "✅ Uploaded: $(basename "$FILE_PATH")"
            log_message "SUCCESS: Uploaded $FILE_PATH"
        else
            echo "❌ Upload failed: $FILE_PATH"
            log_message "ERROR: Upload failed $FILE_PATH"
        fi
        ;;
        
    "download")
        if [ -z "$FILE_PATH" ]; then
            echo "ERROR: File name required"
            exit 1
        fi
        
        log_message "Downloading: $FILE_PATH"
        mega-get "/$FILE_PATH" "."
        if [ $? -eq 0 ]; then
            echo "✅ Downloaded: $FILE_PATH"
            log_message "SUCCESS: Downloaded $FILE_PATH"
        else
            echo "❌ Download failed: $FILE_PATH"
            log_message "ERROR: Download failed $FILE_PATH"
        fi
        ;;
        
    "list")
        log_message "Listing MEGA files"
        mega-ls
        ;;
        
    "sync")
        log_message "Syncing MEGA"
        mega-sync
        echo "✅ MEGA sync completed"
        ;;
        
    *)
        echo "Usage: $0 {upload|download|list|sync} [file_path]"
        echo "Examples:"
        echo "  $0 upload /path/to/file.txt"
        echo "  $0 download myfile.pdf"
        echo "  $0 list"
        echo "  $0 sync"
        exit 1
        ;;
esac