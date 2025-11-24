#!/bin/bash
# Advanced Workspace Launcher Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/workspace_launcher.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
    echo -e "${BLUE}[WORKSPACE]${NC} $1"
}

launch_app() {
    local app_name="$1"
    local command="$2"
    
    log_message "Launching: $app_name"
    
    if command -v "$command" >/dev/null 2>&1; then
        nohup "$command" >/dev/null 2>&1 &
        local pid=$!
        sleep 2
        
        if ps -p $pid > /dev/null 2>&1; then
            log_message "${GREEN}✅ Success: $app_name (PID: $pid)${NC}"
            return 0
        else
            log_message "${YELLOW}⚠️ Process ended: $app_name${NC}"
            return 1
        fi
    else
        log_message "${RED}❌ Command not found: $command${NC}"
        return 1
    fi
}

# Main workspace launch
log_message "Starting complete workspace..."

# Define applications to launch
declare -A apps=(
    ["Google Chrome"]="google-chrome-stable"
    ["Brave Browser"]="brave-browser"
    ["VS Code"]="code"
    ["Spotify"]="spotify"
    ["Discord"]="discord"
    ["Terminal"]="gnome-terminal"
    ["File Manager"]="nautilus"
)

success_count=0
total_count=${#apps[@]}

for app_name in "${!apps[@]}"; do
    if launch_app "$app_name" "${apps[$app_name]}"; then
        ((success_count++))
    fi
    sleep 1
done

log_message "Workspace startup complete: $success_count/$total_count applications"
echo "🎯 Workspace launched: $success_count/$total_count applications"