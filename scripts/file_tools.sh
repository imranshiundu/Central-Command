#!/bin/bash

# C3NTR@L COMM@ND V1.1 - File Tools Script
# File operations, disk management, and backup utilities
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$BASE_DIR/logs"
FILE_OPS_LOG="$LOGS_DIR/file_operations.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$FILE_OPS_LOG"
    
    # Also show in terminal if interactive
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}[ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}[WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}[INFO]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Operation failed: $1"
    exit 1
}

# Safety checks
check_safe_path() {
    local path="$1"
    local resolved_path=$(realpath "$path" 2>/dev/null)
    
    # Prevent directory traversal and sensitive paths
    if [[ "$resolved_path" == /proc/* ]] || \
       [[ "$resolved_path" == /sys/* ]] || \
       [[ "$resolved_path" == /dev/* ]] || \
       [[ "$resolved_path" == /boot/* ]] || \
       [[ "$resolved_path" == /etc/* ]] && \
       [[ "$resolved_path" != "/etc" ]]; then
        log_message "ERROR" "Access to system path denied: $path"
        return 1
    fi
    
    # Check if path is within user's home or project directory
    local user_home="$HOME"
    if [[ ! "$resolved_path" == "$user_home"* ]] && \
       [[ ! "$resolved_path" == "$BASE_DIR"* ]]; then
        log_message "WARNING" "Path outside home/project directory: $path"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 1
        fi
    fi
    
    return 0
}

# File operations
list_files() {
    local path="${1:-.}"
    local detailed="${2:-false}"
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    if [ ! -e "$path" ]; then
        log_message "ERROR" "Path does not exist: $path"
        return 1
    fi
    
    if [ ! -d "$path" ]; then
        log_message "ERROR" "Not a directory: $path"
        return 1
    fi
    
    log_message "INFO" "Listing files in: $path"
    
    if [ "$detailed" = "true" ]; then
        echo "Detailed listing of: $path"
        echo "=========================================="
        ls -la "$path" | head -20
        echo "=========================================="
        
        # Show disk usage
        local total_size=$(du -sh "$path" 2>/dev/null | cut -f1)
        local file_count=$(find "$path" -maxdepth 1 -type f | wc -l)
        local dir_count=$(find "$path" -maxdepth 1 -type d | wc -l)
        ((dir_count--)) # Exclude current directory
        
        echo "Summary:"
        echo "  Total size: $total_size"
        echo "  Files: $file_count"
        echo "  Directories: $dir_count"
    else
        ls -1 "$path" | head -50
    fi
}

search_files() {
    local path="${1:-.}"
    local pattern="$2"
    local max_results="${3:-50}"
    
    if [ -z "$pattern" ]; then
        log_message "ERROR" "Search pattern required"
        echo "Usage: search_files <path> <pattern> [max_results]"
        return 1
    fi
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    log_message "INFO" "Searching for '$pattern' in: $path"
    
    local results
    results=$(find "$path" -name "*$pattern*" -type f 2>/dev/null | head -"$max_results")
    
    if [ -z "$results" ]; then
        log_message "INFO" "No files found matching pattern: $pattern"
        return 0
    fi
    
    echo "Search results for '$pattern':"
    echo "=========================================="
    echo "$results"
    echo "=========================================="
    
    local result_count=$(echo "$results" | wc -l)
    log_message "SUCCESS" "Found $result_count files matching '$pattern'"
}

get_file_info() {
    local file_path="$1"
    
    if [ -z "$file_path" ]; then
        log_message "ERROR" "File path required"
        return 1
    fi
    
    if ! check_safe_path "$file_path"; then
        return 1
    fi
    
    if [ ! -e "$file_path" ]; then
        log_message "ERROR" "File does not exist: $file_path"
        return 1
    fi
    
    log_message "INFO" "Getting info for: $file_path"
    
    echo "File Information:"
    echo "=========================================="
    echo "Path: $(realpath "$file_path")"
    echo "Name: $(basename "$file_path")"
    echo "Type: $(file -b "$file_path")"
    echo "Size: $(du -h "$file_path" | cut -f1)"
    echo "Permissions: $(stat -c "%A" "$file_path")"
    echo "Owner: $(stat -c "%U:%G" "$file_path")"
    echo "Modified: $(stat -c "%y" "$file_path")"
    echo "Accessed: $(stat -c "%x" "$file_path")"
    
    if [ -f "$file_path" ]; then
        local line_count=$(wc -l < "$file_path" 2>/dev/null)
        local word_count=$(wc -w < "$file_path" 2>/dev/null)
        local char_count=$(wc -m < "$file_path" 2>/dev/null)
        
        echo "Lines: $line_count"
        echo "Words: $word_count"
        echo "Characters: $char_count"
        
        # Check if it's a text file
        if file "$file_path" | grep -q "text"; then
            echo "Preview (first 5 lines):"
            echo "------------------------------------------"
            head -5 "$file_path"
            echo "------------------------------------------"
        fi
    fi
    echo "=========================================="
}

copy_file() {
    local source="$1"
    local destination="$2"
    
    if [ -z "$source" ] || [ -z "$destination" ]; then
        log_message "ERROR" "Source and destination paths required"
        return 1
    fi
    
    if ! check_safe_path "$source"; then
        return 1
    fi
    
    if ! check_safe_path "$destination"; then
        return 1
    fi
    
    if [ ! -e "$source" ]; then
        log_message "ERROR" "Source does not exist: $source"
        return 1
    fi
    
    # If destination is directory, copy with same name
    if [ -d "$destination" ]; then
        destination="$destination/$(basename "$source")"
    fi
    
    # Check if destination exists
    if [ -e "$destination" ]; then
        log_message "WARNING" "Destination already exists: $destination"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_message "INFO" "Copy operation cancelled"
            return 0
        fi
    fi
    
    log_message "INFO" "Copying: $source -> $destination"
    
    if cp -r "$source" "$destination" 2>/dev/null; then
        log_message "SUCCESS" "File copied successfully"
        return 0
    else
        log_message "ERROR" "Failed to copy file"
        return 1
    fi
}

move_file() {
    local source="$1"
    local destination="$2"
    
    if [ -z "$source" ] || [ -z "$destination" ]; then
        log_message "ERROR" "Source and destination paths required"
        return 1
    fi
    
    if ! check_safe_path "$source"; then
        return 1
    fi
    
    if ! check_safe_path "$destination"; then
        return 1
    fi
    
    if [ ! -e "$source" ]; then
        log_message "ERROR" "Source does not exist: $source"
        return 1
    fi
    
    # If destination is directory, move with same name
    if [ -d "$destination" ]; then
        destination="$destination/$(basename "$source")"
    fi
    
    # Check if destination exists
    if [ -e "$destination" ]; then
        log_message "WARNING" "Destination already exists: $destination"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_message "INFO" "Move operation cancelled"
            return 0
        fi
    fi
    
    log_message "INFO" "Moving: $source -> $destination"
    
    if mv "$source" "$destination" 2>/dev/null; then
        log_message "SUCCESS" "File moved successfully"
        return 0
    else
        log_message "ERROR" "Failed to move file"
        return 1
    fi
}

delete_file() {
    local target="$1"
    local force="${2:-false}"
    
    if [ -z "$target" ]; then
        log_message "ERROR" "Target path required"
        return 1
    fi
    
    if ! check_safe_path "$target"; then
        return 1
    fi
    
    if [ ! -e "$target" ]; then
        log_message "ERROR" "Target does not exist: $target"
        return 1
    fi
    
    # Extra safety for important directories
    if [[ "$(realpath "$target")" == "$HOME" ]] || \
       [[ "$(realpath "$target")" == "/" ]]; then
        log_message "ERROR" "Cannot delete home or root directory"
        return 1
    fi
    
    if [ "$force" != "true" ]; then
        echo "You are about to delete: $target"
        if [ -d "$target" ]; then
            local item_count=$(find "$target" | wc -l)
            local size=$(du -sh "$target" 2>/dev/null | cut -f1)
            echo "This is a directory containing $item_count items ($size)"
        else
            local size=$(du -h "$target" | cut -f1)
            echo "Size: $size"
        fi
        
        read -p "Are you sure? This cannot be undone! (type 'DELETE' to confirm): " -r
        echo
        if [ "$REPLY" != "DELETE" ]; then
            log_message "INFO" "Delete operation cancelled"
            return 0
        fi
    fi
    
    log_message "WARNING" "Deleting: $target"
    
    if rm -rf "$target" 2>/dev/null; then
        log_message "SUCCESS" "File/directory deleted successfully"
        return 0
    else
        log_message "ERROR" "Failed to delete file/directory"
        return 1
    fi
}

create_directory() {
    local path="$1"
    local parents="${2:-false}"
    
    if [ -z "$path" ]; then
        log_message "ERROR" "Directory path required"
        return 1
    fi
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    if [ -e "$path" ]; then
        log_message "ERROR" "Path already exists: $path"
        return 1
    fi
    
    local mkdir_cmd="mkdir"
    if [ "$parents" = "true" ]; then
        mkdir_cmd="mkdir -p"
    fi
    
    log_message "INFO" "Creating directory: $path"
    
    if $mkdir_cmd "$path" 2>/dev/null; then
        log_message "SUCCESS" "Directory created successfully"
        return 0
    else
        log_message "ERROR" "Failed to create directory"
        return 1
    fi
}

# Disk management functions
check_disk_usage() {
    local path="${1:-.}"
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    log_message "INFO" "Checking disk usage for: $path"
    
    echo "Disk Usage Analysis:"
    echo "=========================================="
    
    # Overall disk usage
    echo "Overall disk usage:"
    df -h "$path" | head -2
    df -h "$path" | tail -1
    
    echo
    echo "Directory sizes (top 10):"
    echo "------------------------------------------"
    du -h --max-depth=1 "$path" 2>/dev/null | sort -hr | head -11
    
    echo
    echo "Large files (top 10):"
    echo "------------------------------------------"
    find "$path" -type f -exec du -h {} + 2>/dev/null | sort -hr | head -10
    
    echo "=========================================="
}

cleanup_temp_files() {
    local path="${1:-/tmp}"
    local age_days="${2:-7}"
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    log_message "INFO" "Cleaning up temp files older than $age_days days in: $path"
    
    local deleted_count=0
    local freed_space=0
    
    # Find and delete old temporary files
    while IFS= read -r -d '' file; do
        if [ -f "$file" ]; then
            local file_size=$(stat -c%s "$file" 2>/dev/null)
            if rm "$file" 2>/dev/null; then
                ((deleted_count++))
                ((freed_space += file_size))
                log_message "INFO" "Deleted: $file"
            fi
        fi
    done < <(find "$path" -type f -mtime "+$age_days" -print0 2>/dev/null)
    
    # Convert freed space to human readable
    local freed_space_human=$(numfmt --to=iec $freed_space)
    
    log_message "SUCCESS" "Cleanup completed: $deleted_count files deleted, $freed_space_human freed"
    echo "Cleanup results:"
    echo "  Files deleted: $deleted_count"
    echo "  Space freed: $freed_space_human"
}

# Backup functions
create_backup() {
    local source="$1"
    local backup_dir="${2:-$BASE_DIR/backups}"
    local backup_name="${3:-backup_$(date +%Y%m%d_%H%M%S)}"
    
    if [ -z "$source" ]; then
        log_message "ERROR" "Source path required"
        return 1
    fi
    
    if ! check_safe_path "$source"; then
        return 1
    fi
    
    if ! check_safe_path "$backup_dir"; then
        return 1
    fi
    
    if [ ! -e "$source" ]; then
        log_message "ERROR" "Source does not exist: $source"
        return 1
    fi
    
    # Create backup directory if it doesn't exist
    mkdir -p "$backup_dir"
    
    local backup_path="$backup_dir/$backup_name.tar.gz"
    
    log_message "INFO" "Creating backup: $source -> $backup_path"
    
    # Show backup size estimate
    local source_size=$(du -sh "$source" 2>/dev/null | cut -f1)
    echo "Backup source: $source ($source_size)"
    echo "Backup destination: $backup_path"
    
    # Create tar archive with progress if available
    if command -v pv >/dev/null 2>&1; then
        tar -cf - "$source" | pv -s "$(du -sb "$source" | cut -f1)" | gzip > "$backup_path"
    else
        tar -czf "$backup_path" "$source"
    fi
    
    if [ $? -eq 0 ]; then
        local backup_size=$(du -h "$backup_path" | cut -f1)
        log_message "SUCCESS" "Backup created successfully: $backup_path ($backup_size)"
        echo "Backup completed: $backup_path ($backup_size)"
        return 0
    else
        log_message "ERROR" "Backup creation failed"
        return 1
    fi
}

restore_backup() {
    local backup_file="$1"
    local restore_path="$2"
    
    if [ -z "$backup_file" ] || [ -z "$restore_path" ]; then
        log_message "ERROR" "Backup file and restore path required"
        return 1
    fi
    
    if ! check_safe_path "$backup_file"; then
        return 1
    fi
    
    if ! check_safe_path "$restore_path"; then
        return 1
    fi
    
    if [ ! -f "$backup_file" ]; then
        log_message "ERROR" "Backup file does not exist: $backup_file"
        return 1
    fi
    
    if [[ ! "$backup_file" =~ \.tar\.gz$ ]]; then
        log_message "ERROR" "Invalid backup file format. Expected .tar.gz"
        return 1
    fi
    
    # Create restore directory if it doesn't exist
    mkdir -p "$restore_path"
    
    log_message "INFO" "Restoring backup: $backup_file -> $restore_path"
    
    echo "Restoring backup to: $restore_path"
    
    if tar -xzf "$backup_file" -C "$restore_path"; then
        log_message "SUCCESS" "Backup restored successfully"
        echo "Restore completed successfully"
        return 0
    else
        log_message "ERROR" "Backup restoration failed"
        return 1
    fi
}

# File analysis
analyze_files() {
    local path="${1:-.}"
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    log_message "INFO" "Analyzing files in: $path"
    
    echo "File System Analysis:"
    echo "=========================================="
    
    # File type distribution
    echo "File type distribution:"
    echo "------------------------------------------"
    find "$path" -type f | sed 's/.*\.//' | sort | uniq -c | sort -nr | head -10
    
    echo
    # Largest files
    echo "Largest files:"
    echo "------------------------------------------"
    find "$path" -type f -exec du -h {} + 2>/dev/null | sort -hr | head -10
    
    echo
    # Most recently modified
    echo "Recently modified files:"
    echo "------------------------------------------"
    find "$path" -type f -exec stat -c "%Y %n" {} + 2>/dev/null | sort -nr | head -10 | while read time file; do
        echo "$(date -d "@$time" '+%Y-%m-%d %H:%M:%S') - $file"
    done
    
    echo
    # Permission analysis
    echo "Permission distribution:"
    echo "------------------------------------------"
    find "$path" -type f -exec stat -c "%A" {} + 2>/dev/null | sort | uniq -c | sort -nr
    
    echo "=========================================="
}

# Utility functions
get_file_count() {
    local path="${1:-.}"
    
    if ! check_safe_path "$path"; then
        return 1
    fi
    
    local file_count=$(find "$path" -type f | wc -l)
    local dir_count=$(find "$path" -type d | wc -l)
    
    echo "File count: $file_count"
    echo "Directory count: $dir_count"
    echo "Total items: $((file_count + dir_count))"
    
    log_message "INFO" "Counted $file_count files and $dir_count directories in $path"
}

calculate_hash() {
    local file_path="$1"
    local algorithm="${2:-sha256}"
    
    if [ -z "$file_path" ]; then
        log_message "ERROR" "File path required"
        return 1
    fi
    
    if ! check_safe_path "$file_path"; then
        return 1
    fi
    
    if [ ! -f "$file_path" ]; then
        log_message "ERROR" "File does not exist: $file_path"
        return 1
    fi
    
    log_message "INFO" "Calculating $algorithm hash for: $file_path"
    
    case $algorithm in
        md5) hash_result=$(md5sum "$file_path" | cut -d' ' -f1) ;;
        sha1) hash_result=$(sha1sum "$file_path" | cut -d' ' -f1) ;;
        sha256) hash_result=$(sha256sum "$file_path" | cut -d' ' -f1) ;;
        *) log_message "ERROR" "Unsupported algorithm: $algorithm"; return 1 ;;
    esac
    
    if [ -n "$hash_result" ]; then
        echo "$algorithm hash: $hash_result"
        log_message "SUCCESS" "Hash calculated: $hash_result"
        return 0
    else
        log_message "ERROR" "Failed to calculate hash"
        return 1
    fi
}

# Main function for script execution
main() {
    local action="$1"
    shift
    
    case "$action" in
        "list")
            list_files "$@"
            ;;
        "search")
            search_files "$@"
            ;;
        "info")
            get_file_info "$@"
            ;;
        "copy")
            copy_file "$@"
            ;;
        "move")
            move_file "$@"
            ;;
        "delete")
            delete_file "$@"
            ;;
        "mkdir")
            create_directory "$@"
            ;;
        "diskusage")
            check_disk_usage "$@"
            ;;
        "cleanup")
            cleanup_temp_files "$@"
            ;;
        "backup")
            create_backup "$@"
            ;;
        "restore")
            restore_backup "$@"
            ;;
        "analyze")
            analyze_files "$@"
            ;;
        "count")
            get_file_count "$@"
            ;;
        "hash")
            calculate_hash "$@"
            ;;
        "help"|"")
            echo "C3NTR@L COMM@ND File Tools"
            echo "==========================="
            echo "Available commands:"
            echo "  list [path] [detailed]    - List files in directory"
            echo "  search <path> <pattern>   - Search for files"
            echo "  info <file>               - Get file information"
            echo "  copy <src> <dest>         - Copy file/directory"
            echo "  move <src> <dest>         - Move file/directory"
            echo "  delete <path> [force]     - Delete file/directory"
            echo "  mkdir <path> [parents]    - Create directory"
            echo "  diskusage [path]          - Check disk usage"
            echo "  cleanup [path] [days]     - Clean up old files"
            echo "  backup <src> [dest] [name]- Create backup"
            echo "  restore <backup> <dest>   - Restore backup"
            echo "  analyze [path]            - Analyze file system"
            echo "  count [path]              - Count files/directories"
            echo "  hash <file> [algorithm]   - Calculate file hash"
            echo "  help                      - Show this help"
            ;;
        *)
            log_message "ERROR" "Unknown action: $action"
            echo "Use 'help' to see available commands"
            return 1
            ;;
    esac
}

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi