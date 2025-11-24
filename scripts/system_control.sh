#!/bin/bash

# C3NTR@L COMM@ND V1.1 - System Control Script
# Power management, session control, and system operations
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BASE_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1"
LOGS_DIR="$BASE_DIR/logs"
SYSTEM_LOG="$LOGS_DIR/system_control.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# System control settings
CONFIRM_DESTRUCTIVE=true
DRY_RUN=false
TIMEOUT_SHUTDOWN=30
TIMEOUT_REBOOT=30

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$SYSTEM_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "SYSTEM") echo -e "${PURPLE}⚙️ [SYSTEM]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "System control operation failed: $1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if running as root, use sudo if not
check_privileges() {
    local operation="$1"
    
    if [[ $EUID -eq 0 ]]; then
        log_message "INFO" "Running as root for: $operation"
        return 0
    else
        log_message "INFO" "Running as user, may need sudo for: $operation"
        return 1
    fi
}

# Confirm destructive actions
confirm_action() {
    local message="$1"
    local destructive="${2:-true}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would ask for confirmation: $message"
        return 0
    fi
    
    if [ "$CONFIRM_DESTRUCTIVE" = false ] && [ "$destructive" = true ]; then
        log_message "WARNING" "Auto-confirming destructive action: $message"
        return 0
    fi
    
    echo -e "${YELLOW}❓ $message (y/N): ${NC}"
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_message "INFO" "User cancelled action: $message"
        return 1
    fi
    return 0
}

# Power management functions
system_shutdown() {
    local delay="${1:-1}"
    
    log_message "SYSTEM" "Initiating system shutdown in ${delay} minutes"
    
    if ! confirm_action "Shutdown system in ${delay} minute(s)?" true; then
        return 1
    fi
    
    echo -e "${RED}🛑 SYSTEM SHUTDOWN INITIATED${NC}"
    echo "System will shutdown in ${delay} minute(s)"
    echo "Use 'shutdown -c' to cancel"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would shutdown system in ${delay} minutes"
        echo "DRY RUN: shutdown -h +${delay}"
        return 0
    fi
    
    # Try multiple shutdown methods
    if check_privileges "shutdown"; then
        shutdown -h +"$delay"
    else
        sudo shutdown -h +"$delay"
    fi
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Shutdown scheduled in ${delay} minutes"
        return 0
    else
        log_message "ERROR" "Failed to schedule shutdown"
        return 1
    fi
}

system_reboot() {
    local delay="${1:-1}"
    
    log_message "SYSTEM" "Initiating system reboot in ${delay} minutes"
    
    if ! confirm_action "Reboot system in ${delay} minute(s)?" true; then
        return 1
    fi
    
    echo -e "${YELLOW}🔄 SYSTEM REBOOT INITIATED${NC}"
    echo "System will reboot in ${delay} minute(s)"
    echo "Use 'shutdown -c' to cancel"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would reboot system in ${delay} minutes"
        echo "DRY RUN: shutdown -r +${delay}"
        return 0
    fi
    
    if check_privileges "reboot"; then
        shutdown -r +"$delay"
    else
        sudo shutdown -r +"$delay"
    fi
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Reboot scheduled in ${delay} minutes"
        return 0
    else
        log_message "ERROR" "Failed to schedule reboot"
        return 1
    fi
}

system_suspend() {
    log_message "SYSTEM" "Attempting to suspend system"
    
    if ! confirm_action "Suspend system to RAM?" false; then
        return 1
    fi
    
    echo -e "${BLUE}💤 SUSPENDING SYSTEM${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would suspend system"
        echo "DRY RUN: systemctl suspend"
        return 0
    fi
    
    # Try multiple suspend methods
    local success=false
    
    if command_exists systemctl; then
        if check_privileges "suspend"; then
            systemctl suspend
        else
            sudo systemctl suspend
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists pm-suspend; then
        if check_privileges "pm-suspend"; then
            pm-suspend
        else
            sudo pm-suspend
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists loginctl; then
        loginctl suspend
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "System suspended successfully"
        return 0
    else
        log_message "ERROR" "All suspend methods failed"
        return 1
    fi
}

system_hibernate() {
    log_message "SYSTEM" "Attempting to hibernate system"
    
    if ! confirm_action "Hibernate system to disk?" false; then
        return 1
    fi
    
    echo -e "${PURPLE}🐻 HIBERNATING SYSTEM${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would hibernate system"
        echo "DRY RUN: systemctl hibernate"
        return 0
    fi
    
    # Try multiple hibernate methods
    local success=false
    
    if command_exists systemctl; then
        if check_privileges "hibernate"; then
            systemctl hibernate
        else
            sudo systemctl hibernate
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists pm-hibernate; then
        if check_privileges "pm-hibernate"; then
            pm-hibernate
        else
            sudo pm-hibernate
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "System hibernated successfully"
        return 0
    else
        log_message "ERROR" "All hibernate methods failed"
        return 1
    fi
}

# Session control functions
lock_screen() {
    log_message "SYSTEM" "Attempting to lock screen"
    
    echo -e "${CYAN}🔒 LOCKING SCREEN${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would lock screen"
        echo "DRY RUN: Multiple lock methods would be attempted"
        return 0
    fi
    
    # Try multiple screen locking methods
    local success=false
    
    if command_exists loginctl; then
        loginctl lock-session
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists gnome-screensaver-command; then
        gnome-screensaver-command --lock
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists xdg-screensaver; then
        xdg-screensaver lock
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists dm-tool; then
        dm-tool lock
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists xscreensaver-command; then
        xscreensaver-command --lock
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "Screen locked successfully"
        return 0
    else
        log_message "ERROR" "All screen lock methods failed"
        return 1
    fi
}

logout_user() {
    local force="${1:-false}"
    
    log_message "SYSTEM" "Attempting to logout user"
    
    if [ "$force" = false ] && ! confirm_action "Logout current user session?" true; then
        return 1
    fi
    
    echo -e "${YELLOW}🚪 LOGGING OUT USER${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would logout user"
        echo "DRY RUN: Multiple logout methods would be attempted"
        return 0
    fi
    
    # Try multiple logout methods
    local success=false
    
    # Get current display
    local display="${DISPLAY:-:0}"
    
    if command_exists loginctl; then
        local session_id=$(loginctl list-sessions --no-legend | grep "$USER" | awk '{print $1}')
        if [ -n "$session_id" ]; then
            loginctl terminate-session "$session_id"
            [ $? -eq 0 ] && success=true
        fi
    fi
    
    if [ "$success" = false ] && command_exists gnome-session-quit; then
        if [ "$force" = true ]; then
            gnome-session-quit --force --no-prompt
        else
            gnome-session-quit --logout --no-prompt
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && [ -n "$display" ]; then
        # Try X11 method
        if command_exists xdotool; then
            export DISPLAY="$display"
            xdotool key --clearmodifiers Alt+F4
            sleep 1
            xdotool key --clearmodifiers Return
            success=true
        fi
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "User logout initiated"
        return 0
    else
        log_message "ERROR" "All logout methods failed"
        return 1
    fi
}

# Process management functions
list_processes() {
    local pattern="${1:-}"
    local max_lines="${2:-20}"
    
    log_message "SYSTEM" "Listing processes${pattern:+" matching: $pattern"}"
    
    echo -e "${CYAN}🔄 RUNNING PROCESSES${NC}"
    echo "=========================================="
    
    if [ -n "$pattern" ]; then
        if command_exists pgrep; then
            local pids=$(pgrep -f "$pattern")
            if [ -n "$pids" ]; then
                ps -p "$pids" -o pid,user,%cpu,%mem,command --no-headers | head -"$max_lines"
            else
                echo "No processes found matching: $pattern"
            fi
        else
            ps aux | grep -v grep | grep -- "$pattern" | head -"$max_lines"
        fi
    else
        ps aux --sort=-%cpu | head -"$((max_lines + 1))"
    fi
    
    echo "=========================================="
}

kill_process() {
    local identifier="$1"
    local signal="${2:-TERM}"
    
    if [ -z "$identifier" ]; then
        log_message "ERROR" "Process identifier required"
        echo "Usage: kill_process <pid|name> [signal]"
        return 1
    fi
    
    log_message "SYSTEM" "Attempting to kill process: $identifier with signal: $signal"
    
    # Check if identifier is PID or name
    if [[ "$identifier" =~ ^[0-9]+$ ]]; then
        # It's a PID
        local pid="$identifier"
        local process_info=$(ps -p "$pid" -o user,command --no-headers 2>/dev/null)
        
        if [ -z "$process_info" ]; then
            log_message "ERROR" "Process with PID $pid not found"
            return 1
        fi
        
        echo "Process: $process_info"
        
        if ! confirm_action "Kill process $pid ($process_info)?" true; then
            return 1
        fi
    else
        # It's a process name
        local pids=$(pgrep -f "$identifier")
        if [ -z "$pids" ]; then
            log_message "ERROR" "No processes found matching: $identifier"
            return 1
        fi
        
        echo "Found processes:"
        for pid in $pids; do
            local process_info=$(ps -p "$pid" -o user,command --no-headers 2>/dev/null)
            echo "  $pid: $process_info"
        done
        
        if ! confirm_action "Kill ${pids//$'\n'/, } ($identifier)?" true; then
            return 1
        fi
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would kill process(es) with signal $signal"
        echo "DRY RUN: kill -$signal $identifier"
        return 0
    fi
    
    # Execute kill
    if [[ "$identifier" =~ ^[0-9]+$ ]]; then
        kill -"$signal" "$identifier"
    else
        pkill -f "$identifier"
    fi
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Process kill signal sent successfully"
        return 0
    else
        log_message "ERROR" "Failed to send kill signal"
        return 1
    fi
}

# Service management functions
service_status() {
    local service_name="$1"
    
    if [ -z "$service_name" ]; then
        log_message "ERROR" "Service name required"
        echo "Usage: service_status <service_name>"
        return 1
    fi
    
    log_message "SYSTEM" "Checking status of service: $service_name"
    
    if command_exists systemctl; then
        systemctl status "$service_name" --no-pager -l
    elif command_exists service; then
        service "$service_name" status
    else
        log_message "ERROR" "No service management tool available"
        return 1
    fi
}

service_control() {
    local service_name="$1"
    local action="$2"
    
    if [ -z "$service_name" ] || [ -z "$action" ]; then
        log_message "ERROR" "Service name and action required"
        echo "Usage: service_control <service_name> <start|stop|restart|reload>"
        return 1
    fi
    
    log_message "SYSTEM" "Attempting to $action service: $service_name"
    
    if ! confirm_action "$action service $service_name?" false; then
        return 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would $action service $service_name"
        echo "DRY RUN: systemctl $action $service_name"
        return 0
    fi
    
    local success=false
    
    if command_exists systemctl; then
        if check_privileges "service_control"; then
            systemctl "$action" "$service_name"
        else
            sudo systemctl "$action" "$service_name"
        fi
        [ $? -eq 0 ] && success=true
    elif command_exists service; then
        if check_privileges "service_control"; then
            service "$service_name" "$action"
        else
            sudo service "$service_name" "$action"
        fi
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "Service $service_name $action successful"
        return 0
    else
        log_message "ERROR" "Failed to $action service $service_name"
        return 1
    fi
}

# Hardware control functions
set_brightness() {
    local level="$1"
    
    if [ -z "$level" ]; then
        log_message "ERROR" "Brightness level required (0-100)"
        echo "Usage: set_brightness <0-100>"
        return 1
    fi
    
    # Validate level
    if [[ ! "$level" =~ ^[0-9]+$ ]] || [ "$level" -lt 0 ] || [ "$level" -gt 100 ]; then
        log_message "ERROR" "Brightness level must be between 0 and 100"
        return 1
    fi
    
    log_message "SYSTEM" "Setting brightness to $level%"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would set brightness to $level%"
        return 0
    fi
    
    local success=false
    
    # Try multiple brightness control methods
    if command_exists brightnessctl; then
        brightnessctl set "${level}%"
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists xbacklight; then
        xbacklight -set "$level"
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && [ -d /sys/class/backlight ]; then
        local backlight_dir=$(find /sys/class/backlight -mindepth 1 -maxdepth 1 | head -1)
        if [ -n "$backlight_dir" ] && [ -f "$backlight_dir/brightness" ] && [ -f "$backlight_dir/max_brightness" ]; then
            local max_brightness=$(cat "$backlight_dir/max_brightness")
            local new_brightness=$((max_brightness * level / 100))
            if check_privileges "brightness"; then
                echo "$new_brightness" > "$backlight_dir/brightness"
            else
                echo "$new_brightness" | sudo tee "$backlight_dir/brightness" > /dev/null
            fi
            [ $? -eq 0 ] && success=true
        fi
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "Brightness set to $level%"
        return 0
    else
        log_message "ERROR" "All brightness control methods failed"
        return 1
    fi
}

set_volume() {
    local level="$1"
    
    if [ -z "$level" ]; then
        log_message "ERROR" "Volume level required (0-100)"
        echo "Usage: set_volume <0-100>"
        return 1
    fi
    
    # Validate level
    if [[ ! "$level" =~ ^[0-9]+$ ]] || [ "$level" -lt 0 ] || [ "$level" -gt 100 ]; then
        log_message "ERROR" "Volume level must be between 0 and 100"
        return 1
    fi
    
    log_message "SYSTEM" "Setting volume to $level%"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would set volume to $level%"
        return 0
    fi
    
    local success=false
    
    # Try multiple volume control methods
    if command_exists pamixer; then
        pamixer --set-volume "$level"
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists amixer; then
        amixer set Master "${level}%"
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = false ] && command_exists pactl; then
        pactl set-sink-volume @DEFAULT_SINK@ "${level}%"
        [ $? -eq 0 ] && success=true
    fi
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "Volume set to $level%"
        return 0
    else
        log_message "ERROR" "All volume control methods failed"
        return 1
    fi
}

# System information functions
system_info() {
    log_message "SYSTEM" "Displaying system information"
    
    echo -e "${GREEN}🖥️ SYSTEM INFORMATION${NC}"
    echo "=========================================="
    
    # Basic system info
    echo "Hostname: $(hostname)"
    echo "OS: $(lsb_release -d 2>/dev/null | cut -f2 || uname -o)"
    echo "Kernel: $(uname -r)"
    echo "Architecture: $(uname -m)"
    echo "Uptime: $(uptime -p)"
    
    # CPU info
    echo
    echo "CPU: $(grep -m 1 "model name" /proc/cpuinfo | cut -d: -f2 | xargs)"
    echo "Cores: $(nproc)"
    
    # Memory info
    echo
    echo "Memory:"
    free -h | awk 'NR<=2{print "  "$0}'
    
    # Disk info
    echo
    echo "Disk:"
    df -h / | awk 'NR==2{print "  "$3 " used / " $2 " total (" $5 ")"}'
    
    # Load average
    echo
    echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    echo "=========================================="
}

# Cancel scheduled shutdown/reboot
cancel_shutdown() {
    log_message "SYSTEM" "Attempting to cancel scheduled shutdown/reboot"
    
    echo -e "${GREEN}✅ CANCELLING SCHEDULED SHUTDOWN${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        log_message "INFO" "DRY RUN: Would cancel scheduled shutdown"
        echo "DRY RUN: shutdown -c"
        return 0
    fi
    
    if check_privileges "shutdown_cancel"; then
        shutdown -c
    else
        sudo shutdown -c
    fi
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Scheduled shutdown cancelled"
        return 0
    else
        log_message "ERROR" "Failed to cancel scheduled shutdown"
        return 1
    fi
}

# Main function
main() {
    local action="$1"
    shift
    
    case "$action" in
        "shutdown")
            system_shutdown "$@"
            ;;
        "reboot")
            system_reboot "$@"
            ;;
        "suspend")
            system_suspend "$@"
            ;;
        "hibernate")
            system_hibernate "$@"
            ;;
        "lock")
            lock_screen "$@"
            ;;
        "logout")
            logout_user "$@"
            ;;
        "processes")
            list_processes "$@"
            ;;
        "kill")
            kill_process "$@"
            ;;
        "service-status")
            service_status "$@"
            ;;
        "service-control")
            service_control "$@"
            ;;
        "brightness")
            set_brightness "$@"
            ;;
        "volume")
            set_volume "$@"
            ;;
        "info")
            system_info "$@"
            ;;
        "cancel-shutdown")
            cancel_shutdown "$@"
            ;;
        "test")
            echo -e "${CYAN}🧪 System Control Test${NC}"
            echo "=========================================="
            system_info
            echo
            list_processes "" 5
            echo
            echo "Testing lock screen..."
            lock_screen
            ;;
        "help"|"--help"|"-h")
            echo -e "${CYAN}C3NTR@L COMM@ND System Control${NC}"
            echo "=========================================="
            echo "Power management, session control, and system operations"
            echo
            echo "Usage: $0 [command] [arguments]"
            echo
            echo "Power Management:"
            echo "  shutdown [delay]     - Shutdown system (default: 1 minute)"
            echo "  reboot [delay]       - Reboot system (default: 1 minute)"
            echo "  suspend              - Suspend to RAM"
            echo "  hibernate            - Hibernate to disk"
            echo "  cancel-shutdown      - Cancel scheduled shutdown"
            echo
            echo "Session Control:"
            echo "  lock                 - Lock screen"
            echo "  logout [force]       - Logout user (--force for no prompt)"
            echo
            echo "Process Management:"
            echo "  processes [pattern]  - List running processes"
            echo "  kill <pid|name> [signal] - Kill process (default: TERM)"
            echo
            echo "Service Management:"
            echo "  service-status <name> - Show service status"
            echo "  service-control <name> <action> - Control service"
            echo "    Actions: start, stop, restart, reload"
            echo
            echo "Hardware Control:"
            echo "  brightness <0-100>   - Set display brightness"
            echo "  volume <0-100>       - Set audio volume"
            echo
            echo "Information:"
            echo "  info                 - Show system information"
            echo "  test                 - Run system control tests"
            echo "  help                 - Show this help message"
            echo
            echo "Options:"
            echo "  --dry-run           - Preview actions without executing"
            echo "  --no-confirm        - Skip confirmation prompts"
            echo
            echo "Examples:"
            echo "  $0 shutdown 5        # Shutdown in 5 minutes"
            echo "  $0 reboot 0          # Reboot immediately"
            echo "  $0 lock              # Lock screen"
            echo "  $0 kill firefox      # Kill Firefox processes"
            echo "  $0 brightness 75     # Set brightness to 75%"
            echo "  $0 volume 50         # Set volume to 50%"
            ;;
        *)
            if [ -n "$action" ]; then
                echo -e "${RED}Unknown command: $action${NC}"
            fi
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
        --no-confirm)
            CONFIRM_DESTRUCTIVE=false
            shift
            ;;
        *)
            break
            ;;
    esac
done

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_message "INFO" "System control script started with arguments: $*"
    main "$@"
    exit $?
fi