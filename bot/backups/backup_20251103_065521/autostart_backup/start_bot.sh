#!/bin/bash

# C3NTR@L COMM@ND V1.1 - Advanced Auto-Start Manager
# ENHANCED VERSION with advanced monitoring and features

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1/bot"  # ✅ FIXED PATH
VENV_PYTHON="/home/imran/snap/C3NTR@L-COMM@ND-V1.1/.venv/bin/python3"  # ✅ FIXED VENV PATH
LOG_DIR="$BOT_DIR/logs"
CONFIG_FILE="$BOT_DIR/config.json"
PID_FILE="$BOT_DIR/bot.pid"
STATUS_FILE="$BOT_DIR/bot.status"
HEARTBEAT_FILE="$BOT_DIR/bot.heartbeat"
LOCK_FILE="$BOT_DIR/bot.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "$LOG_DIR" "$BOT_DIR/autostart"

# 🔧 ENHANCED: Configuration loader with caching
CONFIG_CACHE=""
get_config() {
    if [[ -z "$CONFIG_CACHE" && -f "$CONFIG_FILE" ]]; then
        CONFIG_CACHE=$(cat "$CONFIG_FILE")
    fi
    
    if [[ -n "$CONFIG_CACHE" ]]; then
        echo "$CONFIG_CACHE" | python3 -c "
import json, sys
try:
    config = json.loads(sys.stdin.read())
    print(config.get('$1', '$2'))
except:
    print('$2')
"
    else
        echo "$2"
    fi
}

# 🔧 ENHANCED: Advanced notification system
send_telegram_message() {
    local message="$1"
    local token=$(get_config "telegram_bot_token" "")
    local chat_id=$(get_config "authorized_user_ids" "[]" | python3 -c "import sys, json; ids=json.loads(sys.stdin.read()); print(ids[0] if ids else '')")
    
    if [[ -n "$token" && -n "$chat_id" ]]; then
        # URL encode the message
        local encoded_message=$(echo "$message" | python3 -c "
import urllib.parse, sys
print(urllib.parse.quote(sys.stdin.read()))
")
        curl -s --max-time 10 -X POST "https://api.telegram.org/bot$token/sendMessage" \
            -d "chat_id=$chat_id" \
            -d "text=$encoded_message" \
            -d "parse_mode=Markdown" > /dev/null 2>&1 &
    fi
}

# 🔧 NEW: Emergency notification system
send_emergency_alert() {
    local title="$1"
    local message="$2"
    local priority="$3"
    
    # Telegram
    send_telegram_message "🚨 $title 🚨\n$message"
    
    # Desktop notification with urgency
    if command -v notify-send >/dev/null 2>&1; then
        local urgency="normal"
        [[ "$priority" == "high" ]] && urgency="critical"
        notify-send "🚨 $title" "$message" -u "$urgency" -t 10000 &
    fi
    
    # 🔧 NEW: System log for critical events
    logger -t "C3NTRAL-BOT" "EMERGENCY: $title - $message"
    
    # 🔧 NEW: Flash screen for critical alerts (if supported)
    if [[ "$priority" == "critical" ]] && command -v xflock4 >/dev/null 2>&1; then
        xflock4 &
    fi
}

send_desktop_notification() {
    local title="$1"
    local message="$2"
    
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "$title" "$message" -i "$BOT_DIR/icon.png" -t 5000 2>/dev/null &
    fi
}

send_dual_notification() {
    local title="$1"
    local message="$2"
    local priority="${3:-normal}"
    
    echo "$(date): $title - $message" >> "$LOG_DIR/notifications.log"
    
    if [[ "$priority" == "emergency" ]]; then
        send_emergency_alert "$title" "$message" "high"
    else
        send_telegram_message "*$title*%0A$message"
        send_desktop_notification "$title" "$message"
    fi
}

# 🔧 ENHANCED: Advanced logging system
log() {
    local message="$1"
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $message" | tee -a "$LOG_DIR/autostart.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [INFO] $message" >> "$LOG_DIR/bot_system.log"
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $message" | tee -a "$LOG_DIR/autostart.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [WARN] $message" >> "$LOG_DIR/bot_system.log"
}

log_error() {
    local message="$1"
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $message" | tee -a "$LOG_DIR/autostart.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [ERROR] $message" >> "$LOG_DIR/bot_system.log"
    
    # 🔧 NEW: Auto-report errors to Telegram
    if check_internet; then
        send_telegram_message "❌ Bot Error Occurred\n*Error:* $message\n*Time:* $(date '+%Y-%m-%d %H:%M:%S')"
    fi
}

log_info() {
    local message="$1"
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $message" | tee -a "$LOG_DIR/autostart.log"
}

# 🔧 ENHANCED: Internet checking with fallback methods
check_internet() {
    local timeout=10
    local methods=(
        "curl -s --max-time $timeout -I https://www.google.com >/dev/null 2>&1"
        "ping -c 1 -W 5 8.8.8.8 >/dev/null 2>&1"
        "wget -q --spider --timeout=$timeout http://www.github.com >/dev/null 2>&1"
        "nc -zw1 8.8.8.8 443 >/dev/null 2>&1"
    )
    
    for method in "${methods[@]}"; do
        if eval "$method"; then
            return 0
        fi
    done
    return 1
}

# 🔧 ENHANCED: Network information with multiple interfaces
get_network_info() {
    local ip_info=""
    local ssid_info=""
    local signal_info=""
    
    # Get all IP addresses
    ip_info=$(hostname -I 2>/dev/null | tr ' ' ',' | head -1)
    [[ -z "$ip_info" ]] && ip_info="No IP"
    
    # Get WiFi info
    if command -v iwgetid >/dev/null 2>&1; then
        ssid_info=$(iwgetid -r 2>/dev/null || echo "Ethernet")
    else
        ssid_info="Ethernet"
    fi
    
    # Get signal strength if available
    if [[ -f "/proc/net/wireless" ]]; then
        signal_info=$(cat /proc/net/wireless 2>/dev/null | awk 'NR==3 {print int($3*100/70)"%"}' || echo "N/A")
    else
        signal_info="N/A"
    fi
    
    echo "IP: $ip_info | Network: $ssid_info | Signal: $signal_info"
}

# 🔧 ENHANCED: System information with more details
get_system_info() {
    local uptime=$(uptime -p 2>/dev/null | sed 's/^up //' || echo "Unknown")
    local battery="N/A"
    local load=$(cat /proc/loadavg 2>/dev/null | cut -d' ' -f1-3 || echo "Unknown")
    local memory=$(free -h 2>/dev/null | awk 'NR==2{print $3"/"$2}' || echo "Unknown")
    
    # Battery info
    if ls /sys/class/power_supply/BAT* >/dev/null 2>&1; then
        battery=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo "N/A")
    fi
    
    # 🔧 NEW: Disk usage
    local disk_usage=$(df -h / | awk 'NR==2{print $5}')
    
    echo "Uptime: $uptime | Battery: ${battery}% | Load: $load | Memory: $memory | Disk: $disk_usage"
}

# 🔧 ENHANCED: Resource monitoring with thresholds
check_resources() {
    local cpu_threshold=85
    local memory_threshold=90
    local disk_threshold=90
    
    # CPU usage
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1 | cut -d'.' -f1)
    
    # Memory usage
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3/$2 * 100}')
    
    # Disk usage
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    # Check thresholds
    if [[ "$cpu_usage" -gt "$cpu_threshold" ]]; then
        log_warning "High CPU usage: ${cpu_usage}%"
        [[ "$cpu_usage" -gt 95 ]] && send_dual_notification "⚠️ High CPU Usage" "CPU at ${cpu_usage}% - consider closing some applications" "emergency"
    fi
    
    if [[ "$memory_usage" -gt "$memory_threshold" ]]; then
        log_warning "High memory usage: ${memory_usage}%"
        send_dual_notification "⚠️ High Memory Usage" "Memory at ${memory_usage}% - system may become slow"
    fi
    
    if [[ "$disk_usage" -gt "$disk_threshold" ]]; then
        log_warning "High disk usage: ${disk_usage}%"
        send_dual_notification "⚠️ Low Disk Space" "Disk usage at ${disk_usage}% - consider cleaning up"
    fi
}

# 🔧 ENHANCED: Process management with lock file
acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid=$(cat "$LOCK_FILE" 2>/dev/null)
        if kill -0 "$lock_pid" 2>/dev/null; then
            return 1
        fi
    fi
    echo $$ > "$LOCK_FILE"
    return 0
}

release_lock() {
    rm -f "$LOCK_FILE"
}

is_bot_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            # Check if it's actually our bot process
            if ps -p "$pid" -o command= | grep -q "python.*main.py"; then
                return 0
            else
                # Stale PID file
                rm -f "$PID_FILE"
            fi
        else
            # Process doesn't exist
            rm -f "$PID_FILE"
        fi
    fi
    return 1
}

# 🔧 ENHANCED: Bot startup with better error handling
start_bot() {
    if ! acquire_lock; then
        log_error "Another instance is already starting the bot"
        return 1
    fi
    
    if is_bot_running; then
        log_info "Bot is already running (PID: $(cat "$PID_FILE"))"
        release_lock
        return 0
    fi
    
    log "🚀 Starting C3NTR@L COMM@ND bot..."
    
    # Change to bot directory
    cd "$BOT_DIR" || {
        log_error "Failed to change to bot directory: $BOT_DIR"
        release_lock
        return 1
    }
    
    # 🔧 FIXED: Use absolute path to virtual environment Python
    if [[ -f "$VENV_PYTHON" ]]; then
        log_info "Using virtual environment: $VENV_PYTHON"
        nohup "$VENV_PYTHON" main.py >> "$LOG_DIR/bot_console.log" 2>&1 &
    else
        log_warning "Virtual environment not found, using system Python"
        nohup python3 main.py >> "$LOG_DIR/bot_console.log" 2>&1 &
    fi
    
    local bot_pid=$!
    
    # Save PID
    echo $bot_pid > "$PID_FILE"
    
    # Wait and check if started successfully
    sleep 5
    if is_bot_running; then
        log "✅ Bot started successfully (PID: $bot_pid)"
        echo "RUNNING" > "$STATUS_FILE"
        echo "$(date +%s)" > "$HEARTBEAT_FILE"
        
        # 🔧 ENHANCED: Send comprehensive startup notification
        local network_info=$(get_network_info)
        local system_info=$(get_system_info)
        send_dual_notification "🤖 C3NTR@L COMM@ND Online" "System started successfully!\n\n$system_info\n$network_info\nPID: $bot_pid"
        
        release_lock
        return 0
    else
        log_error "❌ Bot failed to start (PID: $bot_pid)"
        
        # 🔧 ENHANCED: Detailed error diagnostics
        if [[ -f "$LOG_DIR/bot_console.log" ]]; then
            log_error "Last 10 lines of bot console:"
            tail -10 "$LOG_DIR/bot_console.log" | while read line; do
                log_error "  $line"
            done
        fi
        
        rm -f "$PID_FILE"
        release_lock
        
        # 🔧 NEW: Auto-retry once
        log_info "Attempting auto-retry..."
        sleep 2
        start_bot
        return $?
    fi
}

# 🔧 ENHANCED: Graceful shutdown
stop_bot() {
    if ! acquire_lock; then
        log_error "Another operation in progress, cannot stop bot"
        return 1
    fi
    
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        log "🛑 Stopping bot (PID: $pid)..."
        
        # Graceful shutdown with timeout
        kill -TERM "$pid" 2>/dev/null
        
        local timeout=15
        while (( timeout > 0 )) && is_bot_running; do
            sleep 1
            ((timeout--))
        done
        
        # Force kill if still running
        if is_bot_running; then
            log_warning "Bot didn't stop gracefully, forcing kill..."
            kill -KILL "$pid" 2>/dev/null
            sleep 2
        fi
        
        if is_bot_running; then
            log_error "Failed to stop bot process"
            release_lock
            return 1
        else
            rm -f "$PID_FILE"
            echo "STOPPED" > "$STATUS_FILE"
            log "✅ Bot stopped successfully"
            send_dual_notification "🛑 C3NTR@L COMM@ND Offline" "Bot service has been stopped\nTime: $(date '+%Y-%m-%d %H:%M:%S')"
        fi
    else
        log_info "Bot is not running"
    fi
    
    release_lock
}

# 🔧 ENHANCED: Smart restart
restart_bot() {
    log "🔄 Restarting bot..."
    if stop_bot; then
        sleep 3
        start_bot
    else
        log_error "Failed to stop bot during restart"
        return 1
    fi
}

# 🔧 ENHANCED: Health monitoring with diagnostics
monitor_bot_health() {
    if ! is_bot_running; then
        log_error "❌ Bot is not running! Attempting auto-restart..."
        if start_bot; then
            send_dual_notification "🔧 Bot Auto-Recovered" "Bot was down but has been automatically restarted" "emergency"
        else
            send_dual_notification "🚨 Bot Recovery Failed" "Bot is down and auto-restart failed! Manual intervention required." "emergency"
        fi
        return $?
    fi
    
    # Update heartbeat
    echo "$(date +%s)" > "$HEARTBEAT_FILE"
    
    # Check responsiveness
    local last_heartbeat=$(cat "$HEARTBEAT_FILE" 2>/dev/null || echo "0")
    local current_time=$(date +%s)
    local time_diff=$((current_time - last_heartbeat))
    
    if (( time_diff > 300 )); then  # 5 minutes without heartbeat
        log_warning "⚠️ Bot appears unresponsive (last heartbeat: ${time_diff}s ago). Restarting..."
        restart_bot
    fi
    
    # Resource monitoring
    check_resources
    
    # 🔧 NEW: Check bot functionality
    check_bot_functionality
}

# 🔧 NEW: Bot functionality check
check_bot_functionality() {
    local bot_pid=$(cat "$PID_FILE" 2>/dev/null)
    if [[ -n "$bot_pid" ]]; then
        # Check if bot process is consuming CPU (indicating it's working)
        local cpu_usage=$(ps -p "$bot_pid" -o %cpu --no-headers 2>/dev/null | tr -d ' ' || echo "0")
        
        if [[ "$cpu_usage" == "0.0" ]] || [[ -z "$cpu_usage" ]]; then
            log_warning "Bot process seems idle (CPU: ${cpu_usage}%)"
        fi
    fi
}

# 🔧 ENHANCED: Connection state tracking
last_connection_state="unknown"
track_connection() {
    if check_internet; then
        if [[ "$last_connection_state" != "connected" ]]; then
            log "✅ Internet connection restored"
            local network_info=$(get_network_info)
            send_dual_notification "🌐 Connection Restored" "Back online and ready for commands!\n$network_info"
            last_connection_state="connected"
        fi
        echo "ONLINE" > "$BOT_DIR/connection.status"
    else
        if [[ "$last_connection_state" != "disconnected" ]]; then
            log_warning "🌐 Internet connection lost"
            send_desktop_notification "🌐 Connection Lost" "Working offline - commands will be queued"
            last_connection_state="disconnected"
        fi
        echo "OFFLINE" > "$BOT_DIR/connection.status"
    fi
}

# 🔧 NEW: Performance metrics collection
collect_metrics() {
    local metrics_file="$LOG_DIR/performance_metrics.log"
    echo "$(date '+%Y-%m-%d %H:%M:%S'),$(uptime -p | sed 's/up //'),$(cat /proc/loadavg | cut -d' ' -f1),$(free | awk 'NR==2{printf "%.1f", $3/$2*100}'),$(df / | awk 'NR==2{print $5}' | sed 's/%//')" >> "$metrics_file"
    
    # Keep only last 1000 entries
    tail -1000 "$metrics_file" > "$metrics_file.tmp" && mv "$metrics_file.tmp" "$metrics_file"
}

# 🔧 ENHANCED: Main monitoring loop with performance tracking
run_monitor_loop() {
    log "🔍 Starting advanced monitor loop..."
    local loop_count=0
    local last_metrics_collection=0
    
    # 🔧 NEW: Startup diagnostics
    send_dual_notification "🔧 Monitor Started" "Advanced monitoring system activated\nBot Directory: $BOT_DIR\nLogs: $LOG_DIR"
    
    while true; do
        ((loop_count++))
        
        # Track connection status
        track_connection
        
        # Monitor bot health every 30 seconds
        if (( loop_count % 6 == 0 )); then  # 30 seconds
            monitor_bot_health
        fi
        
        # Collect performance metrics every minute
        if (( loop_count % 12 == 0 )); then  # 1 minute
            collect_metrics
        fi
        
        # Send periodic status every 15 minutes
        if (( loop_count % 180 == 0 )); then  # 15 minutes
            if check_internet && is_bot_running; then
                local network_info=$(get_network_info)
                local system_info=$(get_system_info)
                local bot_pid=$(cat "$PID_FILE" 2>/dev/null || echo "N/A")
                send_telegram_message "💚 System Status Update\n*Uptime:* $(uptime -p)\n*Bot PID:* $bot_pid\n$system_info\n$network_info\n*Loop Count:* $loop_count"
            fi
        fi
        
        # 🔧 NEW: Comprehensive log rotation every hour
        if (( loop_count % 720 == 0 )); then  # 1 hour
            log_info "🔄 Performing comprehensive log maintenance..."
            find "$LOG_DIR" -name "*.log" -type f -size +10M -exec gzip {} \;
            find "$LOG_DIR" -name "*.gz" -mtime +7 -delete
            echo "$(date): Log maintenance completed" >> "$LOG_DIR/maintenance.log"
        fi
        
        # 🔧 NEW: System health check every 2 hours
        if (( loop_count % 1440 == 0 )); then  # 2 hours
            log_info "🏥 Performing system health check..."
            check_resources
        fi
        
        sleep 5
    done
}

# 🔧 NEW: System diagnostics command
system_diagnostics() {
    echo -e "${CYAN}🤖 C3NTR@L COMM@ND System Diagnostics${NC}"
    echo "=========================================="
    
    echo -e "\n${YELLOW}Bot Status:${NC}"
    if is_bot_running; then
        echo -e "  ${GREEN}✅ Running (PID: $(cat "$PID_FILE"))${NC}"
    else
        echo -e "  ${RED}❌ Not running${NC}"
    fi
    
    echo -e "\n${YELLOW}Network Status:${NC}"
    if check_internet; then
        echo -e "  ${GREEN}✅ Connected${NC}"
        echo -e "  $(get_network_info)"
    else
        echo -e "  ${RED}❌ Disconnected${NC}"
    fi
    
    echo -e "\n${YELLOW}System Info:${NC}"
    echo -e "  $(get_system_info)"
    
    echo -e "\n${YELLOW}File Status:${NC}"
    for file in "$PID_FILE" "$STATUS_FILE" "$HEARTBEAT_FILE" "$CONFIG_FILE"; do
        if [[ -f "$file" ]]; then
            echo -e "  ${GREEN}✅ $(basename "$file")${NC}"
        else
            echo -e "  ${RED}❌ $(basename "$file")${NC}"
        fi
    done
    
    echo -e "\n${YELLOW}Recent Logs:${NC}"
    tail -5 "$LOG_DIR/autostart.log" 2>/dev/null | while read line; do
        echo "  $line"
    done
}

# 🔧 NEW: Cleanup command
cleanup_system() {
    log "🧹 Performing system cleanup..."
    
    # Remove stale PID files
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ! kill -0 "$pid" 2>/dev/null; then
            rm -f "$PID_FILE"
            log "Removed stale PID file"
        fi
    fi
    
    # Remove old lock files
    find "$BOT_DIR" -name "*.lock" -mmin +30 -delete 2>/dev/null
    
    # Cleanup old logs
    find "$LOG_DIR" -name "*.log.*" -mtime +7 -delete 2>/dev/null
    
    log "✅ Cleanup completed"
}

# Command line interface
case "${1:-}" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        if is_bot_running; then
            echo -e "${GREEN}✅ Bot is running (PID: $(cat "$PID_FILE"))${NC}"
            if check_internet; then
                echo -e "${GREEN}🌐 Internet: Connected${NC}"
            else
                echo -e "${YELLOW}🌐 Internet: Disconnected${NC}"
            fi
            echo -e "${BLUE}💻 $(get_system_info)${NC}"
        else
            echo -e "${RED}❌ Bot is not running${NC}"
        fi
        ;;
    monitor)
        run_monitor_loop
        ;;
    diagnostics|diag)
        system_diagnostics
        ;;
    cleanup)
        cleanup_system
        ;;
    enable-autostart)
        log "Enabling auto-start..."
        # Implementation for auto-start enable
        ;;
    disable-autostart)
        log "Disabling auto-start..."
        # Implementation for auto-start disable
        ;;
    logs)
        echo -e "${CYAN}📋 Live Logs (Ctrl+C to exit)${NC}"
        tail -f "$LOG_DIR/autostart.log" "$LOG_DIR/bot_console.log" 2>/dev/null
        ;;
    version|--version|-v)
        echo -e "${PURPLE}C3NTR@L COMM@ND Auto-Start Manager v2.0${NC}"
        echo "Advanced monitoring and management system"
        ;;
    *)
        echo -e "${CYAN}🤖 C3NTR@L COMM@ND Auto-Start Manager v2.0${NC}"
        echo "=================================================="
        echo ""
        echo -e "${GREEN}Core Commands:${NC}"
        echo "  start       - Start the bot"
        echo "  stop        - Stop the bot"
        echo "  restart     - Restart the bot"
        echo "  status      - Check bot status"
        echo ""
        echo -e "${YELLOW}Monitoring:${NC}"
        echo "  monitor     - Run advanced monitoring loop"
        echo "  diagnostics - Run comprehensive system diagnostics"
        echo ""
        echo -e "${BLUE}Maintenance:${NC}"
        echo "  cleanup     - Cleanup system files and logs"
        echo "  logs        - Show real-time logs"
        echo ""
        echo -e "${PURPLE}Info:${NC}"
        echo "  version     - Show version information"
        echo ""
        echo -e "Bot Directory: ${BOT_DIR}"
        echo -e "Log Directory: ${LOG_DIR}"
        exit 1
        ;;
esac