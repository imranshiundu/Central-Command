#!/bin/bash

# C3NTR@L COMM@ND V1.1 - Workspace Controller Script
# Application launching, media control, and file management
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="/home/imran/C3NTR@L-COMM@ND-V1.1"
LOGS_DIR="$BASE_DIR/logs"
WORKSPACE_LOG="$LOGS_DIR/workspace_controller.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Application configurations
DEFAULT_MUSIC_PLAYER="vlc"
DEFAULT_VIDEO_PLAYER="vlc"
DEFAULT_BROWSER="google-chrome-stable"

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$WORKSPACE_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "WORKSPACE") echo -e "${PURPLE}🚀 [WORKSPACE]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Workspace operation failed: $1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Launch application with error handling
launch_app() {
    local app_name="$1"
    local app_display_name="$2"
    
    log_message "WORKSPACE" "Launching: $app_display_name"
    
    case "$app_name" in
        "chrome")
            if command_exists google-chrome-stable; then
                nohup google-chrome-stable --disable-features=VizDisplayCompositor >/dev/null 2>&1 &
            elif command_exists chromium-browser; then
                nohup chromium-browser --disable-features=VizDisplayCompositor >/dev/null 2>&1 &
            else
                log_message "ERROR" "Chrome/Chromium not found"
                return 1
            fi
            ;;
            
        "brave")
            if command_exists brave-browser; then
                nohup brave-browser --disable-features=VizDisplayCompositor >/dev/null 2>&1 &
            else
                log_message "ERROR" "Brave browser not found"
                return 1
            fi
            ;;
            
        "vscode")
            if command_exists code; then
                nohup code >/dev/null 2>&1 &
            else
                log_message "ERROR" "VSCode not found"
                return 1
            fi
            ;;
            
        "spotify")
            if command_exists spotify; then
                nohup spotify >/dev/null 2>&1 &
            else
                log_message "ERROR" "Spotify not found"
                return 1
            fi
            ;;
            
        "discord")
            if command_exists discord; then
                nohup discord >/dev/null 2>&1 &
            else
                log_message "ERROR" "Discord not found"
                return 1
            fi
            ;;
            
        "terminal")
            if command_exists gnome-terminal; then
                gnome-terminal &
            elif command_exists konsole; then
                konsole &
            elif command_exists xfce4-terminal; then
                xfce4-terminal &
            else
                log_message "ERROR" "Terminal not found"
                return 1
            fi
            ;;
            
        "filemanager")
            if command_exists nautilus; then
                nautilus &
            elif command_exists nemo; then
                nemo &
            elif command_exists thunar; then
                thunar &
            else
                log_message "ERROR" "File manager not found"
                return 1
            fi
            ;;
            
        *)
            log_message "ERROR" "Unknown application: $app_name"
            return 1
            ;;
    esac
    
    local pid=$!
    sleep 2
    if ps -p $pid > /dev/null 2>&1; then
        log_message "SUCCESS" "$app_display_name launched successfully (PID: $pid)"
        return 0
    else
        log_message "ERROR" "$app_display_name failed to start"
        return 1
    fi
}

# Start complete workspace
start_workspace() {
    log_message "WORKSPACE" "Starting complete workspace"
    
    local apps=(
        "chrome Google Chrome"
        "brave Brave Browser" 
        "vscode Visual Studio Code"
        "spotify Spotify"
        "discord Discord"
        "terminal Terminal"
        "filemanager File Manager"
    )
    
    local success_count=0
    local total_count=${#apps[@]}
    
    echo -e "${CYAN}🚀 Starting Workspace${NC}"
    echo "=========================================="
    
    for app_info in "${apps[@]}"; do
        local app_name=$(echo "$app_info" | cut -d' ' -f1)
        local app_display_name=$(echo "$app_info" | cut -d' ' -f2-)
        
        echo -e "${BLUE}➡️ Launching: $app_display_name${NC}"
        
        if launch_app "$app_name" "$app_display_name"; then
            ((success_count++))
            echo -e "${GREEN}✅ Success${NC}"
        else
            echo -e "${RED}❌ Failed${NC}"
        fi
        
        sleep 1
    done
    
    echo "=========================================="
    echo -e "${GREEN}📊 Results: $success_count/$total_count applications started${NC}"
    
    if [ $success_count -eq $total_count ]; then
        log_message "SUCCESS" "All workspace applications started successfully"
    else
        log_message "WARNING" "Some workspace applications failed to start"
    fi
    
    return $((total_count - success_count))
}

# Media control functions
play_music() {
    local file_path="$1"
    local player="${2:-$DEFAULT_MUSIC_PLAYER}"
    
    if [ ! -f "$file_path" ]; then
        log_message "ERROR" "Music file not found: $file_path"
        return 1
    fi
    
    log_message "WORKSPACE" "Playing music: $file_path with $player"
    
    case "$player" in
        "vlc")
            nohup vlc "$file_path" >/dev/null 2>&1 &
            ;;
        "spotify")
            # Spotify doesn't support local files via command line easily
            # This would play through Spotify if the file is in your local files
            nohup spotify >/dev/null 2>&1 &
            ;;
        "mpv")
            nohup mpv "$file_path" >/dev/null 2>&1 &
            ;;
        *)
            nohup "$player" "$file_path" >/dev/null 2>&1 &
            ;;
    esac
    
    local pid=$!
    sleep 2
    if ps -p $pid > /dev/null 2>&1; then
        log_message "SUCCESS" "Music playback started (PID: $pid)"
        return 0
    else
        log_message "ERROR" "Music playback failed to start"
        return 1
    fi
}

play_video() {
    local file_path="$1"
    local player="${2:-$DEFAULT_VIDEO_PLAYER}"
    
    if [ ! -f "$file_path" ]; then
        log_message "ERROR" "Video file not found: $file_path"
        return 1
    fi
    
    log_message "WORKSPACE" "Playing video: $file_path with $player"
    
    case "$player" in
        "vlc")
            nohup vlc "$file_path" >/dev/null 2>&1 &
            ;;
        "mpv")
            nohup mpv "$file_path" >/dev/null 2>&1 &
            ;;
        "celluloid")
            nohup celluloid "$file_path" >/dev/null 2>&1 &
            ;;
        *)
            nohup "$player" "$file_path" >/dev/null 2>&1 &
            ;;
    esac
    
    local pid=$!
    sleep 2
    if ps -p $pid > /dev/null 2>&1; then
        log_message "SUCCESS" "Video playback started (PID: $pid)"
        return 0
    else
        log_message "ERROR" "Video playback failed to start"
        return 1
    fi
}

# Media control using playerctl
media_control() {
    local action="$1"
    
    log_message "WORKSPACE" "Media control: $action"
    
    if ! command_exists playerctl; then
        log_message "ERROR" "playerctl not installed"
        return 1
    fi
    
    case "$action" in
        "play")
            playerctl play
            ;;
        "pause")
            playerctl pause
            ;;
        "stop")
            playerctl stop
            ;;
        "next")
            playerctl next
            ;;
        "prev")
            playerctl previous
            ;;
        "volumeup")
            playerctl volume 0.1+
            ;;
        "volumedown")
            playerctl volume 0.1-
            ;;
        "status")
            playerctl metadata --format "{{artist}} - {{title}}"
            return 0
            ;;
        *)
            log_message "ERROR" "Unknown media action: $action"
            return 1
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "Media control executed: $action"
        return 0
    else
        log_message "ERROR" "Media control failed: $action"
        return 1
    fi
}

# File operations
open_file() {
    local file_path="$1"
    
    if [ ! -e "$file_path" ]; then
        log_message "ERROR" "File not found: $file_path"
        return 1
    fi
    
    log_message "WORKSPACE" "Opening file: $file_path"
    
    if command_exists xdg-open; then
        xdg-open "$file_path"
    elif command_exists gnome-open; then
        gnome-open "$file_path"
    else
        log_message "ERROR" "No file opener found (xdg-open or gnome-open)"
        return 1
    fi
    
    if [ $? -eq 0 ]; then
        log_message "SUCCESS" "File opened: $file_path"
        return 0
    else
        log_message "ERROR" "Failed to open file: $file_path"
        return 1
    fi
}

# List applications
list_applications() {
    log_message "INFO" "Listing available applications"
    
    echo -e "${CYAN}📱 Available Applications${NC}"
    echo "=========================================="
    echo -e "${BLUE}🌐 Browsers:${NC}"
    echo "  • chrome (Google Chrome)"
    echo "  • brave (Brave Browser)"
    echo "  • firefox (Firefox)"
    echo ""
    echo -e "${GREEN}💻 Development:${NC}"
    echo "  • vscode (Visual Studio Code)"
    echo "  • pycharm (PyCharm)"
    echo "  • webstorm (WebStorm)"
    echo "  • terminal (Terminal)"
    echo ""
    echo -e "${PURPLE}💬 Communication:${NC}"
    echo "  • discord (Discord)"
    echo "  • slack (Slack)"
    echo "  • telegram (Telegram Desktop)"
    echo ""
    echo -e "${YELLOW}🎵 Media:${NC}"
    echo "  • spotify (Spotify)"
    echo "  • vlc (VLC Media Player)"
    echo "  • celluloid (Celluloid)"
    echo "  • mpv (MPV Player)"
    echo ""
    echo -e "${CYAN}📊 Productivity:${NC}"
    echo "  • libreoffice (LibreOffice)"
    echo "  • calculator (Calculator)"
    echo "  • filemanager (File Manager)"
    echo ""
    echo -e "${RED}⚙️ System:${NC}"
    echo "  • settings (System Settings)"
    echo ""
    echo -e "${GREEN}☁️ Cloud:${NC}"
    echo "  • mega (MEGA Sync)"
    echo "=========================================="
}

# Main function
main() {
    local command="$1"
    shift
    
    case "$command" in
        "workspace")
            start_workspace
            ;;
        "launch")
            if [ $# -eq 0 ]; then
                log_message "ERROR" "No application specified"
                echo "Usage: $0 launch <app_name>"
                return 1
            fi
            launch_app "$1" "$1"
            ;;
        "listapps")
            list_applications
            ;;
        "playmusic")
            if [ $# -eq 0 ]; then
                log_message "ERROR" "No music file specified"
                echo "Usage: $0 playmusic <file_path> [player]"
                return 1
            fi
            play_music "$1" "$2"
            ;;
        "playvideo")
            if [ $# -eq 0 ]; then
                log_message "ERROR" "No video file specified"
                echo "Usage: $0 playvideo <file_path> [player]"
                return 1
            fi
            play_video "$1" "$2"
            ;;
        "mediacontrol")
            if [ $# -eq 0 ]; then
                log_message "ERROR" "No media action specified"
                echo "Usage: $0 mediacontrol <play|pause|stop|next|prev|volumeup|volumedown|status>"
                return 1
            fi
            media_control "$1"
            ;;
        "openfile")
            if [ $# -eq 0 ]; then
                log_message "ERROR" "No file specified"
                echo "Usage: $0 openfile <file_path>"
                return 1
            fi
            open_file "$1"
            ;;
        "help"|"")
            echo -e "${CYAN}C3NTR@L COMM@ND V1.1 - Workspace Controller${NC}"
            echo "=========================================="
            echo -e "${GREEN}Available Commands:${NC}"
            echo "  workspace    - Start complete workspace"
            echo "  launch       - Launch specific application"
            echo "  listapps     - List all available applications"
            echo "  playmusic    - Play music file"
            echo "  playvideo    - Play video file"
            echo "  mediacontrol - Control media playback"
            echo "  openfile     - Open file with default app"
            echo "  help         - Show this help message"
            echo ""
            echo -e "${YELLOW}Examples:${NC}"
            echo "  $0 workspace"
            echo "  $0 launch vscode"
            echo "  $0 playmusic /path/to/song.mp3"
            echo "  $0 mediacontrol play"
            echo "=========================================="
            ;;
        *)
            log_message "ERROR" "Unknown command: $command"
            echo "Use '$0 help' for available commands"
            return 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"