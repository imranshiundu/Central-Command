#!/bin/bash

# C3NTR@L COMM@ND V1.1 - System Report Script
# Comprehensive system status and health reporting
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1"
LOGS_DIR="$BASE_DIR/logs"
REPORT_LOG="$LOGS_DIR/system_report.log"
REPORT_DIR="$BASE_DIR/reports"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Report settings
REPORT_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
REPORT_FILE="$REPORT_DIR/system_report_${REPORT_TIMESTAMP}.txt"
DETAILED_MODE=false
INCLUDE_HISTORY=true
MAX_REPORT_DAYS=7

# Ensure directories exist
mkdir -p "$LOGS_DIR" "$REPORT_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$REPORT_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "REPORT") echo -e "${PURPLE}📊 [REPORT]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Report generation failed: $1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get system uptime and load
get_system_uptime() {
    echo -e "${CYAN}🖥️ System Uptime & Load${NC}"
    echo "=========================================="
    
    local uptime_info=$(uptime)
    echo "Uptime: $uptime_info"
    
    # Extract load averages
    local load_avgs=$(echo "$uptime_info" | awk -F'load average:' '{print $2}')
    local cpu_cores=$(nproc)
    
    echo "CPU Cores: $cpu_cores"
    echo "Load Averages: $load_avgs"
    
    # Load analysis
    local load1=$(echo "$load_avgs" | awk -F, '{print $1}' | xargs)
    local load_per_core=$(echo "scale=2; $load1 / $cpu_cores" | bc)
    
    echo -n "Load Analysis: "
    if (( $(echo "$load_per_core < 0.7" | bc -l) )); then
        echo -e "${GREEN}✅ Optimal${NC}"
    elif (( $(echo "$load_per_core < 1.0" | bc -l) )); then
        echo -e "${YELLOW}⚠️ High${NC}"
    else
        echo -e "${RED}❌ Critical${NC}"
    fi
    
    echo "=========================================="
}

# Get memory usage information
get_memory_info() {
    echo -e "${CYAN}💾 Memory Usage${NC}"
    echo "=========================================="
    
    if command_exists free; then
        local mem_info=$(free -h)
        echo "$mem_info"
        
        # Memory usage percentage
        local total_mem=$(free | awk 'NR==2{print $2}')
        local used_mem=$(free | awk 'NR==2{print $3}')
        local mem_percent=$((used_mem * 100 / total_mem))
        
        echo -n "Memory Usage: $mem_percent% - "
        if [ $mem_percent -lt 70 ]; then
            echo -e "${GREEN}✅ Good${NC}"
        elif [ $mem_percent -lt 85 ]; then
            echo -e "${YELLOW}⚠️ High${NC}"
        else
            echo -e "${RED}❌ Critical${NC}"
        fi
        
        # Swap usage
        local swap_total=$(free | awk 'NR==3{print $2}')
        local swap_used=$(free | awk 'NR==3{print $3}')
        if [ $swap_total -gt 0 ]; then
            local swap_percent=$((swap_used * 100 / swap_total))
            echo -n "Swap Usage: $swap_percent% - "
            if [ $swap_percent -lt 50 ]; then
                echo -e "${GREEN}✅ Good${NC}"
            elif [ $swap_percent -lt 80 ]; then
                echo -e "${YELLOW}⚠️ High${NC}"
            else
                echo -e "${RED}❌ Critical${NC}"
            fi
        fi
    else
        echo "free command not available"
    fi
    
    echo "=========================================="
}

# Get disk usage information
get_disk_info() {
    echo -e "${CYAN}💿 Disk Usage${NC}"
    echo "=========================================="
    
    if command_exists df; then
        # Show main filesystems with human readable output
        df -h | grep -E "^(/dev/|Filesystem)" | head -10
        
        # Disk usage analysis
        echo
        echo "Disk Usage Analysis:"
        echo "------------------------------------------"
        
        # Check root filesystem
        local root_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
        echo -n "Root FS: $root_usage% - "
        if [ $root_usage -lt 80 ]; then
            echo -e "${GREEN}✅ Good${NC}"
        elif [ $root_usage -lt 90 ]; then
            echo -e "${YELLOW}⚠️ High${NC}"
        else
            echo -e "${RED}❌ Critical${NC}"
        fi
        
        # Check home directory
        if df ~ >/dev/null 2>&1; then
            local home_usage=$(df ~ | awk 'NR==2{print $5}' | sed 's/%//')
            echo -n "Home FS: $home_usage% - "
            if [ $home_usage -lt 80 ]; then
                echo -e "${GREEN}✅ Good${NC}"
            elif [ $home_usage -lt 90 ]; then
                echo -e "${YELLOW}⚠️ High${NC}"
            else
                echo -e "${RED}❌ Critical${NC}"
            fi
        fi
        
        # Large directories
        if [ "$DETAILED_MODE" = true ]; then
            echo
            echo "Large Directories in /home:"
            echo "------------------------------------------"
            du -sh /home/* 2>/dev/null | sort -hr | head -5
        fi
    else
        echo "df command not available"
    fi
    
    echo "=========================================="
}

# Get CPU information
get_cpu_info() {
    echo -e "${CYAN}⚡ CPU Information${NC}"
    echo "=========================================="
    
    # CPU model
    if [ -f /proc/cpuinfo ]; then
        local cpu_model=$(grep -m 1 "model name" /proc/cpuinfo | cut -d: -f2 | xargs)
        echo "Model: $cpu_model"
        
        local cpu_cores=$(nproc)
        echo "Cores: $cpu_cores"
        
        # CPU frequency
        if [ -f /proc/cpuinfo ]; then
            local cpu_mhz=$(grep -m 1 "cpu MHz" /proc/cpuinfo | cut -d: -f2 | xargs)
            if [ -n "$cpu_mhz" ]; then
                local cpu_ghz=$(echo "scale=2; $cpu_mhz / 1000" | bc)
                echo "Frequency: ${cpu_ghz} GHz"
            fi
        fi
        
        # CPU temperature (if available)
        if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
            local temp=$(cat /sys/class/thermal/thermal_zone0/temp)
            local temp_c=$((temp / 1000))
            echo -n "Temperature: ${temp_c}°C - "
            if [ $temp_c -lt 60 ]; then
                echo -e "${GREEN}✅ Good${NC}"
            elif [ $temp_c -lt 80 ]; then
                echo -e "${YELLOW}⚠️ Warm${NC}"
            else
                echo -e "${RED}❌ Hot${NC}"
            fi
        fi
    else
        echo "CPU information not available"
    fi
    
    echo "=========================================="
}

# Get network information
get_network_info() {
    echo -e "${CYAN}🌐 Network Information${NC}"
    echo "=========================================="
    
    # Public IP
    echo -n "Public IP: "
    if command_exists curl; then
        local public_ip=$(curl -s --connect-timeout 3 https://api.ipify.org)
        if [ -n "$public_ip" ]; then
            echo "$public_ip"
        else
            echo -e "${YELLOW}Unavailable${NC}"
        fi
    else
        echo -e "${YELLOW}curl not available${NC}"
    fi
    
    # Local IPs
    echo
    echo "Local IP Addresses:"
    echo "------------------------------------------"
    if command_exists ip; then
        ip -o addr show | grep -v "127.0.0.1" | grep -v "::1" | awk '{print $2, $4}' | while read interface ip; do
            if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ ]]; then
                echo "  $interface: $ip"
            fi
        done
    elif command_exists ifconfig; then
        ifconfig | grep "inet " | grep -v "127.0.0.1" | awk '{print "  "$2}'
    else
        echo "  Network tools not available"
    fi
    
    # Network connectivity
    echo
    echo "Network Connectivity:"
    echo "------------------------------------------"
    local test_hosts=("8.8.8.8" "google.com")
    for host in "${test_hosts[@]}"; do
        echo -n "  $host: "
        if ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Reachable${NC}"
        else
            echo -e "${RED}❌ Unreachable${NC}"
        fi
    done
    
    # Network interfaces status
    if [ "$DETAILED_MODE" = true ]; then
        echo
        echo "Interface Statistics:"
        echo "------------------------------------------"
        if command_exists ip; then
            ip -s link show | grep -E "^[0-9]+:" | head -5
        fi
    fi
    
    echo "=========================================="
}

# Get process information
get_process_info() {
    echo -e "${CYAN}🔄 Process Information${NC}"
    echo "=========================================="
    
    # Total processes
    local total_procs=$(ps aux --no-headers | wc -l)
    echo "Total Processes: $total_procs"
    
    # Top CPU processes
    echo
    echo "Top CPU Processes:"
    echo "------------------------------------------"
    ps aux --sort=-%cpu | head -6 | awk '{printf "%-10s %-8s %-6s %s\n", $2, $1, $3"%", $11}'
    
    # Top memory processes
    echo
    echo "Top Memory Processes:"
    echo "------------------------------------------"
    ps aux --sort=-%mem | head -6 | awk '{printf "%-10s %-8s %-6s %s\n", $2, $1, $4"%", $11}'
    
    # Zombie processes
    local zombies=$(ps aux | awk '{print $8}' | grep -c Z)
    if [ $zombies -gt 0 ]; then
        echo
        echo -e "${RED}❌ Zombie Processes: $zombies${NC}"
    else
        echo
        echo -e "${GREEN}✅ No zombie processes${NC}"
    fi
    
    echo "=========================================="
}

# Get security status
get_security_info() {
    echo -e "${CYAN}🛡️ Security Status${NC}"
    echo "=========================================="
    
    # Failed login attempts
    if [ -f /var/log/auth.log ]; then
        local failed_logins=$(grep "Failed password" /var/log/auth.log 2>/dev/null | wc -l)
        echo "Failed Login Attempts (recent): $failed_logins"
    elif [ -f /var/log/secure ]; then
        local failed_logins=$(grep "Failed password" /var/log/secure 2>/dev/null | wc -l)
        echo "Failed Login Attempts (recent): $failed_logins"
    else
        echo "Failed Login Attempts: Logs unavailable"
    fi
    
    # SSH status
    echo -n "SSH Service: "
    if systemctl is-active ssh >/dev/null 2>&1 || systemctl is-active sshd >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Active${NC}"
    else
        echo -e "${YELLOW}⚠️ Inactive${NC}"
    fi
    
    # Firewall status
    echo -n "Firewall: "
    if command_exists ufw; then
        if ufw status | grep -q "Status: active"; then
            echo -e "${GREEN}✅ Active${NC}"
        else
            echo -e "${RED}❌ Inactive${NC}"
        fi
    elif command_exists firewall-cmd; then
        if firewall-cmd --state >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Active${NC}"
        else
            echo -e "${RED}❌ Inactive${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️ Unknown${NC}"
    fi
    
    # System updates
    echo -n "System Updates: "
    if command_exists apt-get; then
        local updates=$(apt list --upgradable 2>/dev/null | wc -l)
        if [ $updates -gt 1 ]; then
            echo -e "${YELLOW}⚠️ $((updates-1)) available${NC}"
        else
            echo -e "${GREEN}✅ Up to date${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️ Unknown${NC}"
    fi
    
    # Suspicious processes
    echo
    echo "Suspicious Process Check:"
    echo "------------------------------------------"
    local suspicious_procs=$(ps aux | grep -E "(miner|backdoor|malware)" | grep -v grep | wc -l)
    if [ $suspicious_procs -eq 0 ]; then
        echo -e "${GREEN}✅ No obvious suspicious processes${NC}"
    else
        echo -e "${RED}❌ Suspicious processes detected${NC}"
    fi
    
    echo "=========================================="
}

# Get C3NTR@L COMM@ND system status
get_bot_status() {
    echo -e "${CYAN}🤖 C3NTR@L COMM@ND Status${NC}"
    echo "=========================================="
    
    # Check if bot is running
    echo -n "Bot Process: "
    if pgrep -f "main.py" >/dev/null; then
        echo -e "${GREEN}✅ Running${NC}"
        
        # Get bot uptime
        local bot_pid=$(pgrep -f "main.py")
        if [ -n "$bot_pid" ]; then
            local bot_start=$(ps -p "$bot_pid" -o lstart= 2>/dev/null)
            if [ -n "$bot_start" ]; then
                echo "Bot Started: $bot_start"
            fi
        fi
    else
        echo -e "${RED}❌ Not Running${NC}"
    fi
    
    # Check module directories
    echo
    echo "Module Status:"
    echo "------------------------------------------"
    
    local modules=("camera_tools.py" "file_manager.py" "network_tools.py" "system_control.py" "security_tools.py" "scheduler.py")
    local base_bot_dir="$BASE_DIR/bot"
    
    for module in "${modules[@]}"; do
        local module_path="$base_bot_dir/modules/$module"
        if [ -f "$module_path" ]; then
            echo -e "  $module: ${GREEN}✅ Present${NC}"
        else
            echo -e "  $module: ${RED}❌ Missing${NC}"
        fi
    done
    
    # Check logs
    echo
    echo "Log Files:"
    echo "------------------------------------------"
    
    local log_files=("bot_activity.log" "system_report.log")
    for log_file in "${log_files[@]}"; do
        local log_path="$LOGS_DIR/$log_file"
        if [ -f "$log_path" ]; then
            local log_size=$(du -h "$log_path" | cut -f1)
            local log_lines=$(wc -l < "$log_path" 2>/dev/null)
            echo "  $log_file: $log_size ($log_lines lines)"
        else
            echo -e "  $log_file: ${RED}❌ Missing${NC}"
        fi
    done
    
    # Check disk usage for bot directory
    echo
    echo "Bot Disk Usage:"
    echo "------------------------------------------"
    local bot_size=$(du -sh "$BASE_DIR" 2>/dev/null | cut -f1)
    echo "Total Size: $bot_size"
    
    echo "=========================================="
}

# Get system services status
get_services_info() {
    echo -e "${CYAN}⚙️ System Services${NC}"
    echo "=========================================="
    
    if command_exists systemctl; then
        # Critical services
        local critical_services=("ssh" "networking" "dbus" "cron")
        
        for service in "${critical_services[@]}"; do
            echo -n "$service: "
            if systemctl is-active "$service" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Active${NC}"
            elif systemctl is-active "${service}d" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Active${NC}"
            else
                echo -e "${RED}❌ Inactive${NC}"
            fi
        done
        
        # Failed services
        echo
        echo "Failed Services:"
        echo "------------------------------------------"
        local failed_services=$(systemctl --failed --no-legend | wc -l)
        if [ $failed_services -eq 0 ]; then
            echo -e "${GREEN}✅ No failed services${NC}"
        else
            echo -e "${RED}❌ $failed_services failed services${NC}"
            if [ "$DETAILED_MODE" = true ]; then
                systemctl --failed --no-legend | head -5
            fi
        fi
    else
        echo "systemctl not available"
    fi
    
    echo "=========================================="
}

# Generate summary report
generate_summary() {
    echo -e "${PURPLE}📈 System Health Summary${NC}"
    echo "=========================================="
    
    local health_score=100
    local warnings=0
    local errors=0
    
    # Check disk space
    local root_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//' 2>/dev/null || echo "0")
    if [ $root_usage -gt 90 ]; then
        ((health_score -= 20))
        ((errors++))
        echo -e "${RED}❌ CRITICAL: Disk usage $root_usage%${NC}"
    elif [ $root_usage -gt 80 ]; then
        ((health_score -= 10))
        ((warnings++))
        echo -e "${YELLOW}⚠️ WARNING: Disk usage $root_usage%${NC}"
    fi
    
    # Check memory
    if command_exists free; then
        local total_mem=$(free | awk 'NR==2{print $2}')
        local used_mem=$(free | awk 'NR==2{print $3}')
        local mem_percent=$((used_mem * 100 / total_mem))
        
        if [ $mem_percent -gt 90 ]; then
            ((health_score -= 15))
            ((errors++))
            echo -e "${RED}❌ CRITICAL: Memory usage $mem_percent%${NC}"
        elif [ $mem_percent -gt 80 ]; then
            ((health_score -= 8))
            ((warnings++))
            echo -e "${YELLOW}⚠️ WARNING: Memory usage $mem_percent%${NC}"
        fi
    fi
    
    # Check load
    local load1=$(uptime | awk -F'load average:' '{print $2}' | awk -F, '{print $1}' | xargs)
    local cpu_cores=$(nproc)
    local load_per_core=$(echo "scale=2; $load1 / $cpu_cores" | bc)
    
    if (( $(echo "$load_per_core > 1.5" | bc -l) )); then
        ((health_score -= 15))
        ((errors++))
        echo -e "${RED}❌ CRITICAL: High load $load1${NC}"
    elif (( $(echo "$load_per_core > 1.0" | bc -l) )); then
        ((health_score -= 8))
        ((warnings++))
        echo -e "${YELLOW}⚠️ WARNING: Elevated load $load1${NC}"
    fi
    
    # Check bot status
    if ! pgrep -f "main.py" >/dev/null; then
        ((health_score -= 10))
        ((errors++))
        echo -e "${RED}❌ CRITICAL: Bot not running${NC}"
    fi
    
    # Final health assessment
    echo
    echo "Overall Health Score: $health_score/100"
    if [ $health_score -ge 90 ]; then
        echo -e "${GREEN}✅ EXCELLENT: System is healthy${NC}"
    elif [ $health_score -ge 75 ]; then
        echo -e "${GREEN}✅ GOOD: System is in good condition${NC}"
    elif [ $health_score -ge 60 ]; then
        echo -e "${YELLOW}⚠️ FAIR: System needs attention${NC}"
    else
        echo -e "${RED}❌ POOR: System requires immediate attention${NC}"
    fi
    
    echo "Issues: $errors errors, $warnings warnings"
    echo "=========================================="
}

# Clean up old reports
cleanup_old_reports() {
    log_message "INFO" "Cleaning up old reports"
    
    find "$REPORT_DIR" -name "system_report_*.txt" -mtime +$MAX_REPORT_DAYS -delete 2>/dev/null
    local remaining_reports=$(find "$REPORT_DIR" -name "system_report_*.txt" | wc -l)
    
    log_message "SUCCESS" "Cleaned old reports, kept $remaining_reports recent reports"
}

# Generate full system report
generate_full_report() {
    local report_type="${1:-standard}"
    
    log_message "REPORT" "Generating $report_type system report"
    
    # Create report header
    {
        echo "C3NTR@L COMM@ND V1.1 - System Report"
        echo "Generated: $(date)"
        echo "Hostname: $(hostname)"
        echo "=========================================="
        echo
    } > "$REPORT_FILE"
    
    # Generate report sections based on type
    case "$report_type" in
        "standard")
            {
                generate_summary
                echo
                get_system_uptime
                echo
                get_memory_info
                echo
                get_disk_info
                echo
                get_cpu_info
                echo
                get_network_info
                echo
                get_bot_status
            } >> "$REPORT_FILE"
            ;;
        "detailed")
            DETAILED_MODE=true
            {
                generate_summary
                echo
                get_system_uptime
                echo
                get_memory_info
                echo
                get_disk_info
                echo
                get_cpu_info
                echo
                get_network_info
                echo
                get_process_info
                echo
                get_services_info
                echo
                get_security_info
                echo
                get_bot_status
            } >> "$REPORT_FILE"
            ;;
        "minimal")
            {
                generate_summary
                echo
                get_system_uptime
                echo
                get_memory_info
                echo
                get_disk_info
                echo
                get_network_info
            } >> "$REPORT_FILE"
            ;;
        "security")
            {
                echo "SECURITY FOCUSED REPORT"
                echo "======================"
                echo
                get_security_info
                echo
                get_network_info
                echo
                get_process_info
                echo
                get_services_info
            } >> "$REPORT_FILE"
            ;;
    esac
    
    # Add footer
    {
        echo
        echo "=========================================="
        echo "Report saved to: $REPORT_FILE"
        echo "C3NTR@L COMM@ND V1.1 - $(date)"
    } >> "$REPORT_FILE"
    
    # Display report location
    log_message "SUCCESS" "Report generated: $REPORT_FILE"
    echo
    echo -e "${GREEN}✅ System report generated:${NC}"
    echo "    $REPORT_FILE"
    
    # Show quick summary
    echo
    tail -20 "$REPORT_FILE" | head -15
    
    # Clean up old reports
    cleanup_old_reports
}

# Quick status check
quick_status() {
    log_message "INFO" "Performing quick system status check"
    
    echo -e "${CYAN}⚡ Quick System Status${NC}"
    echo "=========================================="
    
    # Uptime and load
    echo "Uptime: $(uptime -p)"
    echo "Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Memory usage
    if command_exists free; then
        local mem_percent=$(free | awk 'NR==2{printf "%.1f", $3*100/$2}')
        echo "Memory: ${mem_percent}% used"
    fi
    
    # Disk usage
    local disk_usage=$(df / | awk 'NR==2{print $5}')
    echo "Disk: $disk_usage used"
    
    # Bot status
    echo -n "Bot: "
    if pgrep -f "main.py" >/dev/null; then
        echo -e "${GREEN}✅ Running${NC}"
    else
        echo -e "${RED}❌ Stopped${NC}"
    fi
    
    # Network
    echo -n "Network: "
    if ping -c 1 -W 2 8.8.8.8 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Connected${NC}"
    else
        echo -e "${RED}❌ Disconnected${NC}"
    fi
    
    echo "=========================================="
}

# Compare with previous report
compare_reports() {
    local current_report="$REPORT_FILE"
    local previous_report=$(find "$REPORT_DIR" -name "system_report_*.txt" ! -name "*$REPORT_TIMESTAMP*" | sort -r | head -1)
    
    if [ -z "$previous_report" ] || [ ! -f "$previous_report" ]; then
        log_message "WARNING" "No previous report found for comparison"
        echo -e "${YELLOW}⚠️ No previous report found for comparison${NC}"
        return 1
    fi
    
    log_message "INFO" "Comparing with previous report: $(basename "$previous_report")"
    
    echo -e "${PURPLE}📊 Report Comparison${NC}"
    echo "=========================================="
    echo "Current:  $(basename "$current_report")"
    echo "Previous: $(basename "$previous_report")"
    echo "------------------------------------------"
    
    # Simple comparison of key metrics would go here
    # This is a placeholder for more sophisticated comparison
    echo "Comparison feature: Under development"
    echo "=========================================="
}

# Main function
main() {
    local action="${1:-standard}"
    
    case "$action" in
        "standard"|"detailed"|"minimal"|"security")
            generate_full_report "$action"
            ;;
        "quick")
            quick_status
            ;;
        "compare")
            generate_full_report "standard"
            compare_reports
            ;;
        "test")
            echo -e "${CYAN}🧪 System Report Test${NC}"
            echo "=========================================="
            get_system_uptime
            echo
            get_memory_info
            echo
            quick_status
            ;;
        "cleanup")
            cleanup_old_reports
            ;;
        "list")
            echo -e "${CYAN}📋 Available Reports${NC}"
            echo "=========================================="
            find "$REPORT_DIR" -name "system_report_*.txt" -exec ls -la {} \; | sort -k6,7 -r | head -10
            ;;
        "help"|"--help"|"-h")
            echo -e "${CYAN}C3NTR@L COMM@ND System Report${NC}"
            echo "=========================================="
            echo "Comprehensive system status and health reporting"
            echo
            echo "Usage: $0 [report_type]"
            echo
            echo "Report Types:"
            echo "  standard   - Standard system report (default)"
            echo "  detailed   - Detailed report with processes and services"
            echo "  minimal    - Minimal quick overview"
            echo "  security   - Security-focused report"
            echo "  quick      - Quick status check (no file output)"
            echo "  compare    - Generate report and compare with previous"
            echo "  test       - Test report generation"
            echo "  cleanup    - Clean up old reports"
            echo "  list       - List available reports"
            echo "  help       - Show this help message"
            echo
            echo "Examples:"
            echo "  $0 detailed     # Generate detailed report"
            echo "  $0 quick        # Quick status check"
            echo "  $0 security     # Security-focused report"
            echo "  $0 compare      # Compare with previous report"
            ;;
        *)
            echo -e "${RED}Unknown report type: $action${NC}"
            echo "Use '$0 help' for available report types"
            return 1
            ;;
    esac
}

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_message "INFO" "Report script started with arguments: $*"
    main "$@"
    exit $?
fi