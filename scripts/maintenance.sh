#!/bin/bash

# C3NTR@L COMM@ND V1.1 - System Maintenance Script
# System updates, cleanup, monitoring, and optimization
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
LOGS_DIR="$BASE_DIR/logs"
MAINTENANCE_LOG="$LOGS_DIR/maintenance.log"
BACKUP_DIR="$BASE_DIR/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Maintenance settings
MAX_LOG_DAYS=30
MAX_BACKUP_DAYS=7
CLEANUP_SIZE_LIMIT="1G"
DRY_RUN=false
AUTO_YES=false

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$BACKUP_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$MAINTENANCE_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "PROGRESS") echo -e "${CYAN}🔄 [PROGRESS]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Operation failed: $1"
    exit 1
}

# Check if running as root for system operations
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_message "WARNING" "Running as root - be careful with system operations"
        return 0
    else
        log_message "INFO" "Running as user - some system operations may require sudo"
        return 1
    fi
}

# Confirm action
confirm_action() {
    local message="$1"
    
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would ask: $message"
        return 0
    fi
    
    echo -e "${YELLOW}❓ $message (y/N): ${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 1
    fi
    return 0
}

# System information
system_info() {
    log_message "INFO" "Gathering system information"
    
    echo -e "${PURPLE}🖥️  System Information${NC}"
    echo "=========================================="
    
    # OS information
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        echo "OS: $PRETTY_NAME"
    else
        echo "OS: $(uname -s) $(uname -r)"
    fi
    
    # Kernel version
    echo "Kernel: $(uname -r)"
    
    # Uptime
    echo "Uptime: $(uptime -p | sed 's/up //')"
    
    # CPU information
    echo "CPU: $(grep -m 1 "model name" /proc/cpuinfo | cut -d: -f2 | xargs)"
    echo "CPU Cores: $(nproc)"
    
    # Memory information
    local mem_total=$(free -h | grep Mem | awk '{print $2}')
    local mem_used=$(free -h | grep Mem | awk '{print $3}')
    local mem_free=$(free -h | grep Mem | awk '{print $4}')
    echo "Memory: $mem_used/$mem_total used ($mem_free free)"
    
    # Disk information
    echo "Disk: $(df -h / | awk 'NR==2 {print $3 "/" $2 " used (" $5 ")"}')"
    
    # Load average
    echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    echo "=========================================="
}

# Package management
system_update() {
    log_message "PROGRESS" "Starting system updates"
    
    echo -e "${PURPLE}📦 System Updates${NC}"
    echo "=========================================="
    
    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        # Debian/Ubuntu
        log_message "INFO" "Using apt package manager"
        
        echo "Updating package lists..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: apt update"
        else
            sudo apt update
        fi
        
        echo "Checking for upgrades..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: apt list --upgradable"
            UPGRADES=$(apt list --upgradable 2>/dev/null | wc -l)
        else
            UPGRADES=$(apt list --upgradable 2>/dev/null | wc -l)
        fi
        
        if [ "$UPGRADES" -gt 1 ]; then
            echo "Found $((UPGRADES-1)) packages to upgrade"
            
            if confirm_action "Upgrade all packages?"; then
                if [ "$DRY_RUN" = true ]; then
                    log_message "INFO" "DRY RUN: Would run: apt upgrade -y"
                else
                    sudo apt upgrade -y
                fi
            fi
        else
            echo "System is up to date"
        fi
        
        # Clean up
        echo "Cleaning up package cache..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: apt autoremove -y && apt autoclean"
        else
            sudo apt autoremove -y
            sudo apt autoclean
        fi
        
    elif command -v dnf >/dev/null 2>&1; then
        # Fedora
        log_message "INFO" "Using dnf package manager"
        
        echo "Updating system..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: dnf update -y"
        else
            sudo dnf update -y
        fi
        
        echo "Cleaning up..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: dnf autoremove -y && dnf clean all"
        else
            sudo dnf autoremove -y
            sudo dnf clean all
        fi
        
    elif command -v yum >/dev/null 2>&1; then
        # CentOS/RHEL
        log_message "INFO" "Using yum package manager"
        
        echo "Updating system..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: yum update -y"
        else
            sudo yum update -y
        fi
        
        echo "Cleaning up..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: yum autoremove -y && yum clean all"
        else
            sudo yum autoremove -y
            sudo yum clean all
        fi
        
    elif command -v pacman >/dev/null 2>&1; then
        # Arch Linux
        log_message "INFO" "Using pacman package manager"
        
        echo "Updating system..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: pacman -Syu --noconfirm"
        else
            sudo pacman -Syu --noconfirm
        fi
        
        echo "Cleaning up..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would run: pacman -Sc --noconfirm"
        else
            sudo pacman -Sc --noconfirm
        fi
        
    else
        log_message "WARNING" "Unsupported package manager"
        echo "Unsupported package manager - skipping system updates"
        return 1
    fi
    
    log_message "SUCCESS" "System updates completed"
    echo "=========================================="
}

# Disk cleanup functions
cleanup_system() {
    log_message "PROGRESS" "Starting system cleanup"
    
    echo -e "${PURPLE}🧹 System Cleanup${NC}"
    echo "=========================================="
    
    local total_freed=0
    
    # Clean package cache
    echo "Cleaning package caches..."
    if command -v apt-get >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would clean apt cache"
        else
            sudo apt clean
            local freed=$(du -sh /var/cache/apt 2>/dev/null | cut -f1)
            echo "Freed: $freed from apt cache"
        fi
    fi
    
    # Clean temporary files
    echo "Cleaning temporary files..."
    local temp_dirs=("/tmp" "/var/tmp" "$HOME/.cache" "$HOME/.local/share/Trash")
    
    for temp_dir in "${temp_dirs[@]}"; do
        if [ -d "$temp_dir" ]; then
            if [ "$DRY_RUN" = true ]; then
                local temp_size=$(du -sh "$temp_dir" 2>/dev/null | cut -f1)
                log_message "INFO" "DRY RUN: Would clean $temp_dir ($temp_size)"
            else
                local before_size=$(du -sk "$temp_dir" 2>/dev/null | cut -f1)
                sudo find "$temp_dir" -type f -atime +7 -delete 2>/dev/null
                local after_size=$(du -sk "$temp_dir" 2>/dev/null | cut -f1)
                local freed=$((before_size - after_size))
                if [ "$freed" -gt 0 ]; then
                    local freed_human=$(numfmt --to=iec $((freed * 1024)))
                    echo "Freed: $freed_human from $temp_dir"
                    total_freed=$((total_freed + freed))
                fi
            fi
        fi
    done
    
    # Clean browser caches
    echo "Cleaning browser caches..."
    local browser_dirs=(
        "$HOME/.cache/mozilla"
        "$HOME/.cache/google-chrome"
        "$HOME/.config/chromium"
        "$HOME/.cache/chromium"
    )
    
    for browser_dir in "${browser_dirs[@]}"; do
        if [ -d "$browser_dir" ]; then
            if [ "$DRY_RUN" = true ]; then
                local cache_size=$(du -sh "$browser_dir" 2>/dev/null | cut -f1)
                log_message "INFO" "DRY RUN: Would clean $browser_dir ($cache_size)"
            else
                local before_size=$(du -sk "$browser_dir" 2>/dev/null | cut -f1)
                rm -rf "$browser_dir"/Cache/*
                rm -rf "$browser_dir"/Code\ Cache/*
                local after_size=$(du -sk "$browser_dir" 2>/dev/null | cut -f1)
                local freed=$((before_size - after_size))
                if [ "$freed" -gt 0 ]; then
                    local freed_human=$(numfmt --to=iec $((freed * 1024)))
                    echo "Freed: $freed_human from $(basename "$browser_dir")"
                    total_freed=$((total_freed + freed))
                fi
            fi
        fi
    done
    
    # Clean log files
    echo "Rotating and cleaning log files..."
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would rotate logs and clean old log files"
    else
        sudo logrotate -f /etc/logrotate.conf 2>/dev/null
        sudo find /var/log -name "*.log" -type f -mtime +$MAX_LOG_DAYS -delete 2>/dev/null
        sudo find /var/log -name "*.gz" -type f -mtime +$MAX_LOG_DAYS -delete 2>/dev/null
        echo "Cleaned logs older than $MAX_LOG_DAYS days"
    fi
    
    # Clean thumbnails
    echo "Cleaning thumbnail cache..."
    local thumb_dir="$HOME/.cache/thumbnails"
    if [ -d "$thumb_dir" ]; then
        if [ "$DRY_RUN" = true ]; then
            local thumb_size=$(du -sh "$thumb_dir" 2>/dev/null | cut -f1)
            log_message "INFO" "DRY RUN: Would clean $thumb_dir ($thumb_size)"
        else
            local before_size=$(du -sk "$thumb_dir" 2>/dev/null | cut -f1)
            rm -rf "$thumb_dir"/*
            local after_size=$(du -sk "$thumb_dir" 2>/dev/null | cut -f1)
            local freed=$((before_size - after_size))
            if [ "$freed" -gt 0 ]; then
                local freed_human=$(numfmt --to=iec $((freed * 1024)))
                echo "Freed: $freed_human from thumbnails"
                total_freed=$((total_freed + freed))
            fi
        fi
    fi
    
    if [ "$total_freed" -gt 0 ] && [ "$DRY_RUN" = false ]; then
        local total_freed_human=$(numfmt --to=iec $((total_freed * 1024)))
        log_message "SUCCESS" "Cleanup completed - freed $total_freed_human"
        echo "Total freed: $total_freed_human"
    elif [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Cleanup operations previewed"
    else
        log_message "INFO" "No significant space could be freed"
    fi
    
    echo "=========================================="
}

# System monitoring
system_health_check() {
    log_message "PROGRESS" "Starting system health check"
    
    echo -e "${PURPLE}❤️  System Health Check${NC}"
    echo "=========================================="
    
    local warnings=0
    local errors=0
    
    # Check disk space
    echo "Checking disk space..."
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$disk_usage" -gt 90 ]; then
        echo -e "${RED}❌ CRITICAL: Disk usage is ${disk_usage}%${NC}"
        ((errors++))
    elif [ "$disk_usage" -gt 80 ]; then
        echo -e "${YELLOW}⚠️ WARNING: Disk usage is ${disk_usage}%${NC}"
        ((warnings++))
    else
        echo -e "${GREEN}✅ OK: Disk usage is ${disk_usage}%${NC}"
    fi
    
    # Check memory usage
    echo "Checking memory usage..."
    local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$mem_usage" -gt 90 ]; then
        echo -e "${RED}❌ CRITICAL: Memory usage is ${mem_usage}%${NC}"
        ((errors++))
    elif [ "$mem_usage" -gt 80 ]; then
        echo -e "${YELLOW}⚠️ WARNING: Memory usage is ${mem_usage}%${NC}"
        ((warnings++))
    else
        echo -e "${GREEN}✅ OK: Memory usage is ${mem_usage}%${NC}"
    fi
    
    # Check load average
    echo "Checking system load..."
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | xargs)
    local cpu_cores=$(nproc)
    local load_per_core=$(echo "$load_avg" | awk -v cores=$cpu_cores '{print $1/cores}')
    
    if (( $(echo "$load_per_core > 1.0" | bc -l) )); then
        echo -e "${RED}❌ CRITICAL: High load average: $load_avg${NC}"
        ((errors++))
    elif (( $(echo "$load_per_core > 0.7" | bc -l) )); then
        echo -e "${YELLOW}⚠️ WARNING: Elevated load average: $load_avg${NC}"
        ((warnings++))
    else
        echo -e "${GREEN}✅ OK: Load average: $load_avg${NC}"
    fi
    
    # Check for failed services
    echo "Checking system services..."
    if command -v systemctl >/dev/null 2>&1; then
        local failed_services=$(systemctl --failed --no-legend | wc -l)
        if [ "$failed_services" -gt 0 ]; then
            echo -e "${RED}❌ CRITICAL: $failed_services failed system services${NC}"
            systemctl --failed --no-legend
            ((errors++))
        else
            echo -e "${GREEN}✅ OK: No failed system services${NC}"
        fi
    fi
    
    # Check zombie processes
    echo "Checking for zombie processes..."
    local zombies=$(ps aux | awk '{print $8}' | grep -c Z)
    if [ "$zombies" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ WARNING: $zombies zombie processes found${NC}"
        ((warnings++))
    else
        echo -e "${GREEN}✅ OK: No zombie processes${NC}"
    fi
    
    # Summary
    echo "------------------------------------------"
    if [ "$errors" -gt 0 ]; then
        echo -e "${RED}❌ Health check failed: $errors errors, $warnings warnings${NC}"
        log_message "ERROR" "System health check failed: $errors errors, $warnings warnings"
        return 1
    elif [ "$warnings" -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Health check completed with $warnings warnings${NC}"
        log_message "WARNING" "System health check completed with $warnings warnings"
        return 0
    else
        echo -e "${GREEN}✅ System health check passed${NC}"
        log_message "SUCCESS" "System health check passed"
        return 0
    fi
    
    echo "=========================================="
}

# Backup functions
create_system_backup() {
    log_message "PROGRESS" "Starting system backup"
    
    echo -e "${PURPLE}💾 System Backup${NC}"
    echo "=========================================="
    
    local backup_name="system_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    # Backup important directories
    local backup_dirs=(
        "$BASE_DIR"
        "$HOME/.config"
        "$HOME/.local/bin"
    )
    
    local total_size=0
    
    for dir in "${backup_dirs[@]}"; do
        if [ -d "$dir" ]; then
            local dir_name=$(basename "$dir")
            local backup_file="$backup_path/${dir_name}.tar.gz"
            
            echo "Backing up: $dir"
            
            if [ "$DRY_RUN" = true ]; then
                local dir_size=$(du -sk "$dir" 2>/dev/null | cut -f1)
                total_size=$((total_size + dir_size))
                log_message "INFO" "DRY RUN: Would backup $dir ($(numfmt --to=iec $((dir_size * 1024))))"
            else
                tar -czf "$backup_file" -C "$(dirname "$dir")" "$(basename "$dir")" 2>/dev/null
                if [ $? -eq 0 ]; then
                    local file_size=$(du -k "$backup_file" | cut -f1)
                    total_size=$((total_size + file_size))
                    echo "✅ Backed up: $dir_name ($(numfmt --to=iec $((file_size * 1024))))"
                else
                    echo "❌ Failed to backup: $dir_name"
                fi
            fi
        fi
    done
    
    # Backup package lists
    echo "Backing up package lists..."
    if command -v apt-get >/dev/null 2>&1; then
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would backup package lists"
        else
            dpkg --get-selections > "$backup_path/package_list.txt"
            apt-mark showmanual > "$backup_path/manual_packages.txt"
        fi
    fi
    
    if [ "$DRY_RUN" = false ]; then
        local total_size_human=$(numfmt --to=iec $((total_size * 1024)))
        log_message "SUCCESS" "System backup completed: $backup_path ($total_size_human)"
        echo "Backup completed: $backup_path ($total_size_human)"
    else
        local total_size_human=$(numfmt --to=iec $((total_size * 1024)))
        log_message "INFO" "DRY RUN: Would create backup: $backup_path ($total_size_human)"
    fi
    
    # Clean old backups
    cleanup_old_backups
    
    echo "=========================================="
}

cleanup_old_backups() {
    log_message "INFO" "Cleaning up old backups"
    
    if [ "$DRY_RUN" = true ]; then
        local old_backups=$(find "$BACKUP_DIR" -name "system_backup_*" -type d -mtime +$MAX_BACKUP_DAYS | wc -l)
        log_message "INFO" "DRY RUN: Would remove $old_backups old backups"
        return
    fi
    
    find "$BACKUP_DIR" -name "system_backup_*" -type d -mtime +$MAX_BACKUP_DAYS -exec rm -rf {} + 2>/dev/null
    local removed_count=$(find "$BACKUP_DIR" -name "system_backup_*" -type d | wc -l)
    
    log_message "SUCCESS" "Cleaned old backups, kept $removed_count recent backups"
}

# Security maintenance
security_updates() {
    log_message "PROGRESS" "Checking for security updates"
    
    echo -e "${PURPLE}🛡️ Security Updates${NC}"
    echo "=========================================="
    
    if command -v apt-get >/dev/null 2>&1; then
        echo "Checking for security updates..."
        if [ "$DRY_RUN" = true ]; then
            log_message "INFO" "DRY RUN: Would check for security updates"
        else
            local security_updates=$(apt list --upgradable 2>/dev/null | grep -i security | wc -l)
            if [ "$security_updates" -gt 0 ]; then
                echo "Found $security_updates security updates"
                if confirm_action "Install security updates?"; then
                    sudo apt upgrade --only-upgrade security -y
                    log_message "SUCCESS" "Security updates installed"
                else
                    log_message "INFO" "Security updates skipped"
                fi
            else
                echo "No security updates available"
                log_message "SUCCESS" "System is up to date with security patches"
            fi
        fi
    else
        log_message "WARNING" "Security update check not supported for this package manager"
        echo "Security update check not available"
    fi
    
    echo "=========================================="
}

# Performance optimization
optimize_system() {
    log_message "PROGRESS" "Starting system optimization"
    
    echo -e "${PURPLE}⚡ System Optimization${NC}"
    echo "=========================================="
    
    # Clear RAM caches
    echo "Optimizing memory..."
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would clear RAM caches"
    else
        if check_root; then
            echo 3 > /proc/sys/vm/drop_caches
            echo "✅ RAM caches cleared"
        else
            echo "⚠️ Root required to clear RAM caches"
        fi
    fi
    
    # Optimize swap
    echo "Optimizing swap..."
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would optimize swap"
    else
        if check_root; then
            swapoff -a && swapon -a
            echo "✅ Swap optimized"
        else
            echo "⚠️ Root required to optimize swap"
        fi
    fi
    
    # Update database for locate
    echo "Updating locate database..."
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would update locate database"
    else
        if command -v updatedb >/dev/null 2>&1; then
            if check_root; then
                updatedb
                echo "✅ Locate database updated"
            else
                echo "⚠️ Root required to update locate database"
            fi
        else
            echo "⚠️ locate command not available"
        fi
    fi
    
    log_message "SUCCESS" "System optimization completed"
    echo "=========================================="
}

# Full maintenance routine
full_maintenance() {
    log_message "INFO" "Starting full maintenance routine"
    
    echo -e "${CYAN}🛠️  Starting Full System Maintenance${NC}"
    echo "=========================================="
    echo
    
    # System information
    system_info
    echo
    
    # Health check
    if ! system_health_check; then
        if ! confirm_action "Health check found issues. Continue with maintenance?"; then
            log_message "WARNING" "Maintenance cancelled due to health check issues"
            return 1
        fi
    fi
    echo
    
    # Security updates
    security_updates
    echo
    
    # System updates
    if confirm_action "Update system packages?"; then
        system_update
    fi
    echo
    
    # Cleanup
    if confirm_action "Clean up system files and caches?"; then
        cleanup_system
    fi
    echo
    
    # Optimization
    if confirm_action "Optimize system performance?"; then
        optimize_system
    fi
    echo
    
    # Backup
    if confirm_action "Create system backup?"; then
        create_system_backup
    fi
    echo
    
    log_message "SUCCESS" "Full maintenance routine completed"
    echo -e "${GREEN}🎉 Full maintenance routine completed successfully!${NC}"
    echo "=========================================="
}

# Main function
main() {
    local action="${1:-full}"
    
    case "$action" in
        "info")
            system_info
            ;;
        "health")
            system_health_check
            ;;
        "update")
            system_update
            ;;
        "cleanup")
            cleanup_system
            ;;
        "backup")
            create_system_backup
            ;;
        "security")
            security_updates
            ;;
        "optimize")
            optimize_system
            ;;
        "full")
            full_maintenance
            ;;
        "help"|"--help"|"-h")
            echo -e "${CYAN}C3NTR@L COMM@ND System Maintenance${NC}"
            echo "=========================================="
            echo "Usage: $0 [command]"
            echo
            echo "Commands:"
            echo "  info      - Show system information"
            echo "  health    - Run system health check"
            echo "  update    - Update system packages"
            echo "  cleanup   - Clean up system files and caches"
            echo "  backup    - Create system backup"
            echo "  security  - Check and install security updates"
            echo "  optimize  - Optimize system performance"
            echo "  full      - Run full maintenance routine (default)"
            echo "  help      - Show this help message"
            echo
            echo "Options:"
            echo "  --dry-run - Preview actions without executing"
            echo "  -y        - Auto-confirm all prompts"
            echo
            echo "Examples:"
            echo "  $0 full           # Full maintenance"
            echo "  $0 --dry-run full # Preview full maintenance"
            echo "  $0 -y cleanup     # Auto-confirm cleanup"
            ;;
        *)
            echo -e "${RED}Unknown command: $action${NC}"
            echo "Use '$0 help' for available commands"
            return 1
            ;;
    esac
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_message "INFO" "Maintenance script started with arguments: $*"
    main "$@"
    exit $?
fi