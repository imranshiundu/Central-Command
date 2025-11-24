#!/bin/bash

# C3NTR@L COMM@ND V1.1 - Notifications Script
# High-visibility notifications that bypass Do Not Disturb
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1"
LOGS_DIR="$BASE_DIR/logs"
NOTIFICATION_LOG="$LOGS_DIR/notifications.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Notification settings
URGENCY_LEVEL="critical"  # critical, normal, low
TIMEOUT=0                 # 0 = never timeout (until dismissed)
SOUND_ENABLED=true
EMERGENCY_MODE=false
FORCE_DND_BYPASS=true

# Sound files
SOUND_ALERT="/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
SOUND_MESSAGE="/usr/share/sounds/freedesktop/stereo/message.oga"
SOUND_URGENT="/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$NOTIFICATION_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "NOTIFICATION") echo -e "${PURPLE}📢 [NOTIFICATION]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Notification failed: $1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Play notification sound
play_sound() {
    local sound_type="${1:-alert}"
    
    if [ "$SOUND_ENABLED" = false ]; then
        return 0
    fi
    
    local sound_file="$SOUND_ALERT"
    case "$sound_type" in
        "message") sound_file="$SOUND_MESSAGE" ;;
        "urgent") sound_file="$SOUND_URGENT" ;;
        "alert") sound_file="$SOUND_ALERT" ;;
    esac
    
    log_message "INFO" "Playing sound: $sound_type ($sound_file)"
    
    # Try multiple sound players
    if command_exists paplay && [ -f "$sound_file" ]; then
        paplay "$sound_file" &
    elif command_exists aplay; then
        # Generate a beep sound as fallback
        timeout 2 speaker-test -t sine -f 1000 -l 1 >/dev/null 2>&1 &
    elif command_exists beep; then
        beep -f 1000 -l 500 &
    else
        # Ultimate fallback - system bell
        echo -e '\a'
    fi
}

# Check if desktop environment is running
check_desktop_environment() {
    if [ -n "$XDG_CURRENT_DESKTOP" ]; then
        echo "$XDG_CURRENT_DESKTOP"
        return 0
    fi
    
    if [ -n "$DESKTOP_SESSION" ]; then
        echo "$DESKTOP_SESSION"
        return 0
    fi
    
    # Check for running desktop processes
    if pgrep -x "gnome-shell" >/dev/null; then
        echo "GNOME"
    elif pgrep -x "plasmashell" >/dev/null; then
        echo "KDE"
    elif pgrep -x "xfce4-session" >/dev/null; then
        echo "XFCE"
    elif pgrep -x "cinnamon-session" >/dev/null; then
        echo "Cinnamon"
    elif pgrep -x "mate-session" >/dev/null; then
        echo "MATE"
    else
        echo "unknown"
    fi
}

# Bypass Do Not Disturb settings
bypass_dnd() {
    local desktop_env=$(check_desktop_environment)
    
    log_message "INFO" "Attempting DND bypass for: $desktop_env"
    
    case "$desktop_env" in
        "GNOME"|"ubuntu:GNOME")
            # GNOME DND bypass - use critical urgency and special hints
            export XAUTHORITY="$HOME/.Xauthority"
            export DISPLAY=":0"
            ;;
        "KDE"|"plasma")
            # KDE DND bypass
            export XAUTHORITY="$HOME/.Xauthority"
            export DISPLAY=":0"
            ;;
        "XFCE")
            # XFCE usually doesn't have strong DND
            export XAUTHORITY="$HOME/.Xauthority"
            export DISPLAY=":0"
            ;;
        *)
            # Generic X11 bypass
            export XAUTHORITY="$HOME/.Xauthority"
            export DISPLAY=":0"
            ;;
    esac
}

# Method 1: libnotify with DND bypass (primary method)
notify_libnotify() {
    local title="$1"
    local message="$2"
    local urgency="${3:-$URGENCY_LEVEL}"
    local timeout="${4:-$TIMEOUT}"
    
    log_message "NOTIFICATION" "libnotify: [$urgency] $title - $message"
    
    # Force DND bypass
    bypass_dnd
    
    # Build notify-send command with maximum visibility options
    local notify_cmd="notify-send"
    local notify_args=()
    
    # Urgency level (critical bypasses most DND settings)
    notify_args+=("--urgency=$urgency")
    
    # Icon for attention
    notify_args+=("--icon=dialog-warning")
    
    # Category for system event
    notify_args+=("--category=device")
    
    # Never expire for critical messages
    if [ "$timeout" -eq 0 ] && [ "$urgency" = "critical" ]; then
        notify_args+=("--expire-time=0")
    else
        notify_args+=("--expire-time=$timeout")
    fi
    
    # Additional hints for DND bypass
    notify_args+=("--hint=string:desktop-entry:C3NTR@L-COMM@ND")
    notify_args+=("--hint=string:suppress-sound:false")
    
    # Execute notification
    if command_exists notify-send; then
        # Set environment for proper display
        export DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
        
        if "$notify_cmd" "${notify_args[@]}" "$title" "$message"; then
            log_message "SUCCESS" "libnotify notification sent successfully"
            return 0
        else
            log_message "WARNING" "libnotify notification failed"
            return 1
        fi
    else
        log_message "WARNING" "notify-send not available"
        return 1
    fi
}

# Method 2: Zenity dialog (very visible)
notify_zenity() {
    local title="$1"
    local message="$2"
    local urgency="$3"
    
    log_message "NOTIFICATION" "zenity: $title - $message"
    
    if ! command_exists zenity; then
        log_message "WARNING" "zenity not available"
        return 1
    fi
    
    bypass_dnd
    
    local zenity_args=()
    local zenity_type="--info"
    
    # Set dialog type based on urgency
    case "$urgency" in
        "critical") zenity_type="--error" ;;
        "normal") zenity_type="--warning" ;;
        "low") zenity_type="--info" ;;
    esac
    
    zenity_args+=("$zenity_type")
    zenity_args+=("--title=$title")
    zenity_args+=("--text=$message")
    zenity_args+=("--width=400")
    zenity_args+=("--height=200")
    
    # Make it modal (always on top)
    zenity_args+=("--modal")
    
    # No timeout for critical messages
    if [ "$urgency" = "critical" ]; then
        zenity_args+=("--timeout=0")
    else
        zenity_args+=("--timeout=10")
    fi
    
    # Execute in background but capture PID for emergency mode
    if [ "$EMERGENCY_MODE" = true ]; then
        zenity "${zenity_args[@]}" &
        local zenity_pid=$!
        echo $zenity_pid
        return 0
    else
        if zenity "${zenity_args[@]}"; then
            log_message "SUCCESS" "zenity notification sent successfully"
            return 0
        else
            log_message "WARNING" "zenity notification failed or was dismissed"
            return 1
        fi
    fi
}

# Method 3: KDialog (KDE desktop)
notify_kdialog() {
    local title="$1"
    local message="$2"
    local urgency="$3"
    
    log_message "NOTIFICATION" "kdialog: $title - $message"
    
    if ! command_exists kdialog; then
        log_message "WARNING" "kdialog not available"
        return 1
    fi
    
    bypass_dnd
    
    local kdialog_args=()
    local kdialog_type="--msgbox"
    
    case "$urgency" in
        "critical") kdialog_type="--error" ;;
        "normal") kdialog_type="--sorry" ;;
        "low") kdialog_type="--msgbox" ;;
    esac
    
    kdialog_args+=("$kdialog_type")
    kdialog_args+=("$message")
    kdialog_args+=("--title" "$title")
    kdialog_args+=("--geometry" "500x300")
    
    if kdialog "${kdialog_args[@]}"; then
        log_message "SUCCESS" "kdialog notification sent successfully"
        return 0
    else
        log_message "WARNING" "kdialog notification failed"
        return 1
    fi
}

# Method 4: XMessage (fallback - very basic but reliable)
notify_xmessage() {
    local title="$1"
    local message="$2"
    local urgency="$3"
    
    log_message "NOTIFICATION" "xmessage: $title - $message"
    
    if ! command_exists xmessage; then
        log_message "WARNING" "xmessage not available"
        return 1
    fi
    
    bypass_dnd
    
    local xmessage_args=()
    
    xmessage_args+=("-title" "$title")
    xmessage_args+=("-center")
    xmessage_args+=("-buttons" "OK:0")
    
    # Set timeout or make it persistent
    if [ "$urgency" = "critical" ] || [ "$EMERGENCY_MODE" = true ]; then
        xmessage_args+=("-timeout" "0")
    else
        xmessage_args+=("-timeout" "10")
    fi
    
    if xmessage "${xmessage_args[@]}" "$message"; then
        log_message "SUCCESS" "xmessage notification sent successfully"
        return 0
    else
        log_message "WARNING" "xmessage notification failed"
        return 1
    fi
}

# Method 5: Emergency full-screen notification (nuclear option)
notify_emergency() {
    local title="$1"
    local message="$2"
    
    log_message "NOTIFICATION" "EMERGENCY: $title - $message"
    
    # Play urgent sound repeatedly
    for i in {1..3}; do
        play_sound "urgent"
        sleep 1
    done
    
    # Try to create a full-screen overlay
    if command_exists yad; then
        bypass_dnd
        yad --title="$title" \
            --text="<span size='x-large' weight='bold'>🚨 $title 🚨</span>\n\n<span size='large'>$message</span>" \
            --button="Acknowledge:0" \
            --width=600 \
            --height=400 \
            --center \
            --undecorated \
            --skip-taskbar \
            --on-top \
            --sticky &
        local emergency_pid=$!
        echo $emergency_pid
        return 0
    elif command_exists zenity; then
        notify_zenity "🚨 $title 🚨" "$message" "critical"
        return $?
    else
        # Last resort - use xmessage with maximum visibility
        bypass_dnd
        xmessage -title "🚨 $title 🚨" -center -buttons "ACKNOWLEDGE:0" -timeout 0 "$message" &
        local emergency_pid=$!
        echo $emergency_pid
        return 0
    fi
}

# Method 6: Desktop-specific emergency notifications
notify_desktop_emergency() {
    local title="$1"
    local message="$2"
    local desktop_env=$(check_desktop_environment)
    
    log_message "NOTIFICATION" "Desktop emergency: $desktop_env - $title"
    
    case "$desktop_env" in
        "GNOME"|"ubuntu:GNOME")
            # GNOME emergency - use gdialog if available
            if command_exists gdialog; then
                gdialog --title "🚨 $title 🚨" --msgbox "$message" 400 200
                return $?
            else
                notify_emergency "$title" "$message"
            fi
            ;;
        "KDE"|"plasma")
            # KDE emergency - use kdialog with emergency options
            if command_exists kdialog; then
                kdialog --error "$message" --title "🚨 $title 🚨" --geometry 500x400
                return $?
            else
                notify_emergency "$title" "$message"
            fi
            ;;
        *)
            # Generic emergency
            notify_emergency "$title" "$message"
            ;;
    esac
}

# Main notification function with multiple fallbacks
send_notification() {
    local title="$1"
    local message="$2"
    local urgency="${3:-normal}"
    local method="${4:-auto}"
    
    if [ -z "$title" ] || [ -z "$message" ]; then
        log_message "ERROR" "Title and message are required"
        return 1
    fi
    
    log_message "INFO" "Sending notification: [$urgency] $title"
    
    # Play sound based on urgency
    case "$urgency" in
        "critical") play_sound "urgent" ;;
        "normal") play_sound "alert" ;;
        "low") play_sound "message" ;;
    esac
    
    local success=false
    local attempted_methods=()
    
    # Force critical urgency for emergency mode
    if [ "$EMERGENCY_MODE" = true ]; then
        urgency="critical"
    fi
    
    # Try specified method or auto-detect
    case "$method" in
        "libnotify")
            attempted_methods=("libnotify")
            ;;
        "zenity")
            attempted_methods=("zenity")
            ;;
        "kdialog")
            attempted_methods=("kdialog")
            ;;
        "xmessage")
            attempted_methods=("xmessage")
            ;;
        "emergency")
            attempted_methods=("emergency")
            ;;
        "auto"|*)
            # Auto-detect based on desktop environment and urgency
            if [ "$urgency" = "critical" ] || [ "$EMERGENCY_MODE" = true ]; then
                attempted_methods=("emergency" "zenity" "kdialog" "libnotify" "xmessage")
            else
                local desktop_env=$(check_desktop_environment)
                case "$desktop_env" in
                    "GNOME"|"ubuntu:GNOME") attempted_methods=("libnotify" "zenity" "xmessage") ;;
                    "KDE"|"plasma") attempted_methods=("kdialog" "libnotify" "zenity") ;;
                    "XFCE") attempted_methods=("libnotify" "zenity" "xmessage") ;;
                    *) attempted_methods=("libnotify" "zenity" "xmessage" "kdialog") ;;
                esac
            fi
            ;;
    esac
    
    # Try each method until one succeeds
    for method in "${attempted_methods[@]}"; do
        case "$method" in
            "libnotify")
                if notify_libnotify "$title" "$message" "$urgency"; then
                    success=true
                    break
                fi
                ;;
            "zenity")
                if notify_zenity "$title" "$message" "$urgency"; then
                    success=true
                    break
                fi
                ;;
            "kdialog")
                if notify_kdialog "$title" "$message" "$urgency"; then
                    success=true
                    break
                fi
                ;;
            "xmessage")
                if notify_xmessage "$title" "$message" "$urgency"; then
                    success=true
                    break
                fi
                ;;
            "emergency")
                if notify_desktop_emergency "$title" "$message"; then
                    success=true
                    break
                fi
                ;;
        esac
    done
    
    if [ "$success" = true ]; then
        log_message "SUCCESS" "Notification delivered successfully using method: $method"
        return 0
    else
        log_message "ERROR" "All notification methods failed"
        return 1
    fi
}

# Test notification system
test_notifications() {
    log_message "INFO" "Starting notification system test"
    
    echo -e "${CYAN}🔔 Notification System Test${NC}"
    echo "=========================================="
    
    # Test low urgency
    echo "Testing LOW urgency notification..."
    send_notification "Test Notification" "This is a low urgency test message" "low"
    sleep 2
    
    # Test normal urgency
    echo "Testing NORMAL urgency notification..."
    send_notification "Test Notification" "This is a normal urgency test message" "normal"
    sleep 2
    
    # Test critical urgency
    echo "Testing CRITICAL urgency notification..."
    send_notification "🚨 CRITICAL TEST" "This is a critical urgency test message" "critical"
    sleep 2
    
    # Test emergency mode
    echo "Testing EMERGENCY MODE notification..."
    local old_emergency="$EMERGENCY_MODE"
    EMERGENCY_MODE=true
    send_notification "🚨 EMERGENCY TEST" "This is an emergency mode test" "critical"
    EMERGENCY_MODE="$old_emergency"
    
    echo "=========================================="
    log_message "SUCCESS" "Notification system test completed"
}

# Continuous notification (for alerts that need repeating)
continuous_notification() {
    local title="$1"
    local message="$2"
    local interval="${3:-5}"
    local count="${4:-3}"
    
    log_message "INFO" "Starting continuous notification: $title (every ${interval}s, $count times)"
    
    for ((i=1; i<=count; i++)); do
        echo "Notification $i/$count: $title"
        send_notification "$title" "$message" "critical"
        
        if [ $i -lt $count ]; then
            sleep "$interval"
        fi
    done
    
    log_message "SUCCESS" "Continuous notification completed"
}

# Main function
main() {
    local action="$1"
    shift
    
    case "$action" in
        "notify")
            local title="$1"
            local message="$2"
            local urgency="${3:-normal}"
            local method="${4:-auto}"
            
            if [ -z "$title" ] || [ -z "$message" ]; then
                echo "Usage: $0 notify \"Title\" \"Message\" [urgency] [method]"
                echo "Urgency: low, normal, critical"
                echo "Methods: auto, libnotify, zenity, kdialog, xmessage, emergency"
                return 1
            fi
            
            send_notification "$title" "$message" "$urgency" "$method"
            ;;
        "emergency")
            local title="$1"
            local message="$2"
            
            if [ -z "$title" ] || [ -z "$message" ]; then
                echo "Usage: $0 emergency \"Title\" \"Message\""
                return 1
            fi
            
            EMERGENCY_MODE=true
            send_notification "$title" "$message" "critical" "emergency"
            ;;
        "continuous")
            local title="$1"
            local message="$2"
            local interval="${3:-5}"
            local count="${4:-3}"
            
            if [ -z "$title" ] || [ -z "$message" ]; then
                echo "Usage: $0 continuous \"Title\" \"Message\" [interval] [count]"
                return 1
            fi
            
            continuous_notification "$title" "$message" "$interval" "$count"
            ;;
        "test")
            test_notifications
            ;;
        "sound-test")
            echo "Testing sound alerts..."
            play_sound "message"
            sleep 1
            play_sound "alert"
            sleep 1
            play_sound "urgent"
            echo "Sound test completed"
            ;;
        "detect-env")
            local env=$(check_desktop_environment)
            echo "Detected desktop environment: $env"
            ;;
        "help"|"--help"|"-h")
            echo -e "${CYAN}C3NTR@L COMM@ND Notification System${NC}"
            echo "=========================================="
            echo "High-visibility notifications that bypass Do Not Disturb"
            echo
            echo "Usage: $0 [command] [arguments]"
            echo
            echo "Commands:"
            echo "  notify \"Title\" \"Message\" [urgency] [method]"
            echo "     - Send a notification with specified urgency and method"
            echo "     Urgency: low, normal, critical (default: normal)"
            echo "     Methods: auto, libnotify, zenity, kdialog, xmessage, emergency"
            echo
            echo "  emergency \"Title\" \"Message\""
            echo "     - Send emergency notification (bypasses all DND)"
            echo
            echo "  continuous \"Title\" \"Message\" [interval] [count]"
            echo "     - Send repeated notifications (default: every 5s, 3 times)"
            echo
            echo "  test"
            echo "     - Test all notification types and methods"
            echo
            echo "  sound-test"
            echo "     - Test sound alerts"
            echo
            echo "  detect-env"
            echo "     - Detect desktop environment"
            echo
            echo "  help"
            echo "     - Show this help message"
            echo
            echo "Examples:"
            echo "  $0 notify \"Hello\" \"This is a test\" normal"
            echo "  $0 emergency \"ALERT\" \"System compromised!\""
            echo "  $0 continuous \"Warning\" \"Battery low\" 10 5"
            echo "  $0 test"
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

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_message "INFO" "Notification script started with arguments: $*"
    main "$@"
    exit $?
fi