#!/bin/bash

# C3NTR@L COMM@ND V1.3 - Auto-Start Setup Script
# FIXED VERSION - Addresses auto-start issues

set -e  # Exit on any error

echo -e "\033[1;36m"
echo "╔══════════════════════════════════════════════╗"
echo "║           C3NTR@L COMM@ND V1.3              ║"
echo "║           Auto-Start Setup                  ║"
echo "║                                              ║"
echo "║         Advanced Bot Management             ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "\033[0m"

# Configuration (derived from this script's location - works from any clone path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTOSTART_DIR="$SCRIPT_DIR"
SERVICE_NAME="c3ntral-command.service"
SERVICE_FILE="$AUTOSTART_DIR/$SERVICE_NAME"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
BACKUP_DIR="$BOT_DIR/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${GREEN}[SETUP]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[SETUP WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[SETUP ERROR]${NC} $1"
}

log_info() {
    echo -e "${BLUE}[SETUP INFO]${NC} $1"
}

# Check we are not running as root (user services need a real user)
check_user() {
    if [[ "$(whoami)" == "root" ]]; then
        log_error "Do not run this as root - systemd user services belong to a login user."
        log_error "Run as your normal user: $0"
        exit 1
    fi
    log "Running as user: $(whoami)"
}

# Check if bot directory exists
check_bot_directory() {
    if [[ ! -d "$BOT_DIR" ]]; then
        log_error "Bot directory not found: $BOT_DIR"
        log_error "Please check the installation path"
        exit 1
    fi
    
    if [[ ! -f "$BOT_DIR/main.py" ]]; then
        log_error "main.py not found in bot directory"
        log_error "Please ensure the bot is properly installed"
        exit 1
    fi
    
    log "Bot directory verified: $BOT_DIR"
}

# Check if start_bot.sh exists and is functional
check_start_script() {
    if [[ ! -f "$AUTOSTART_DIR/start_bot.sh" ]]; then
        log_error "start_bot.sh not found in: $AUTOSTART_DIR"
        log_error "This is required for auto-start to work"
        log_info "Creating basic start_bot.sh..."
        
        cat > "$AUTOSTART_DIR/start_bot.sh" << EOF
#!/bin/bash
# Basic startup script for C3NTR@L COMM@ND
cd "$BOT_DIR"
python3 main.py
EOF
        
        chmod +x "$AUTOSTART_DIR/start_bot.sh"
        log "Created basic start_bot.sh"
    else
        log "Start script found: $AUTOSTART_DIR/start_bot.sh"
        chmod +x "$AUTOSTART_DIR/start_bot.sh"
    fi
}

# Check if virtual environment exists (repo root or bot dir)
check_virtual_environment() {
    local venv_path=""
    for candidate in "$BOT_DIR/../.venv" "$BOT_DIR/.venv"; do
        if [[ -f "$candidate/bin/python3" ]]; then
            venv_path="$(cd "$candidate" && pwd)"
            break
        fi
    done
    
    if [[ ! -d "$venv_path" ]]; then
        log_warning "Virtual environment not found at: $venv_path"
        log_warning "Using system Python instead"
        return 1
    fi
    
    if [[ ! -f "$venv_path/bin/python3" ]]; then
        log_warning "Python not found in virtual environment"
        return 1
    fi
    
    log "Virtual environment verified: $venv_path"
    return 0
}

# Create necessary directories
create_directories() {
    log "Creating necessary directories..."
    
    local directories=(
        "$AUTOSTART_DIR"
        "$BOT_DIR/logs"
        "$BACKUP_DIR"
        "$SYSTEMD_USER_DIR"
        "$HOME/.config/autostart"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log "Created: $dir"
        else
            log "Directory exists: $dir"
        fi
    done
}

# Make scripts executable
make_scripts_executable() {
    log "Setting script permissions..."
    
    # Ensure autostart directory exists
    mkdir -p "$AUTOSTART_DIR"
    
    local scripts=(
        "$AUTOSTART_DIR/start_bot.sh"
        "$BOT_DIR/manage_bot.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [[ -f "$script" ]]; then
            chmod +x "$script"
            log "Made executable: $script"
        else
            log_warning "Script not found: $script"
        fi
    done
}

# Create the systemd user service (paths derived from the actual install)
create_systemd_service() {
    log "Creating systemd service file..."

    # Prefer a venv python, fall back to system python3
    local python_cmd="python3"
    for candidate in "$BOT_DIR/../.venv/bin/python3" "$BOT_DIR/.venv/bin/python3"; do
        if [[ -x "$candidate" ]]; then
            python_cmd="$(cd "$(dirname "$candidate")" && pwd)/python3"
            break
        fi
    done
    [[ "$python_cmd" == "python3" ]] && log_warning "Using system Python (no venv found)"
    
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=C3NTR@L COMM@ND - Telegram remote-control bot
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=$python_cmd $BOT_DIR/main.py
ExecStop=/bin/kill -TERM \$MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# GUI / session environment for camera & screenshot features
Environment=DISPLAY=:0
Environment=XAUTHORITY=$HOME/.Xauthority
Environment=DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus
Environment=HOME=$HOME
Environment=USER=$(whoami)
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME/.local/bin

UMask=0022

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=default.target
EOF

    log "Systemd service file created: $SERVICE_FILE"
}

# 🔧 CRITICAL FIX: Enhanced systemd service installation
install_systemd_service() {
    log "Installing systemd service..."
    
    # Ensure systemd user directory exists
    mkdir -p "$SYSTEMD_USER_DIR"
    
    # Copy service file to systemd user directory
    if cp "$SERVICE_FILE" "$SYSTEMD_USER_DIR/"; then
        log "Service file copied to: $SYSTEMD_USER_DIR/$SERVICE_NAME"
    else
        log_error "Failed to copy service file to systemd directory"
        return 1
    fi
    
    # 🔧 CRITICAL: Enable user linger for proper user service startup
    log "Enabling user linger for user services..."
    if sudo loginctl enable-linger $(whoami); then
        log "User linger enabled successfully"
    else
        log_warning "Failed to enable user linger with sudo, trying without..."
        if loginctl enable-linger $(whoami); then
            log "User linger enabled"
        else
            log_warning "User linger may not be enabled - this may affect auto-start"
        fi
    fi
    
    # 🔧 CRITICAL: Reload systemd user daemon
    log "Reloading systemd user daemon..."
    if systemctl --user daemon-reload; then
        log "Systemd user daemon reloaded successfully"
    else
        log_error "Failed to reload systemd user daemon"
        return 1
    fi
    
    # 🔧 CRITICAL: Enable the service for auto-start
    log "Enabling systemd service for auto-start..."
    if systemctl --user enable "$SERVICE_NAME"; then
        log "Systemd service enabled: $SERVICE_NAME"
    else
        log_error "Failed to enable systemd service"
        return 1
    fi
    
    # 🔧 NEW: Start the service immediately to test
    log "Starting service immediately to test..."
    if systemctl --user start "$SERVICE_NAME"; then
        log "Service started successfully"
        sleep 2
        if systemctl --user is-active "$SERVICE_NAME" >/dev/null; then
            log "Service is running and active"
        else
            log_warning "Service started but may not be active - checking status..."
            systemctl --user status "$SERVICE_NAME" --no-pager || true
        fi
    else
        log_warning "Service failed to start - checking status..."
        systemctl --user status "$SERVICE_NAME" --no-pager || true
    fi
    
    return 0
}

# 🔧 ENHANCED: Create desktop autostart (backup method)
create_desktop_autostart() {
    log "Creating desktop autostart (backup method)..."
    
    local desktop_file="$HOME/.config/autostart/c3ntral-command.desktop"
    local python_cmd="python3"
    for candidate in "$BOT_DIR/../.venv/bin/python3" "$BOT_DIR/.venv/bin/python3"; do
        if [[ -x "$candidate" ]]; then
            python_cmd="$candidate"
            break
        fi
    done
    
    cat > "$desktop_file" << EOF
[Desktop Entry]
Type=Application
Name=C3NTR@L COMM@ND Bot
Comment=Advanced Telegram bot with monitoring features
Exec=sh -c "sleep 30 && cd $BOT_DIR && $python_cmd main.py"
Icon=utilities-terminal
Terminal=false
StartupNotify=false
X-GNOME-Autostart-Delay=30
X-GNOME-Autostart-enabled=true
Hidden=false
EOF

    chmod +x "$desktop_file"
    log "Desktop autostart created: $desktop_file"
}

# 🔧 ENHANCED: Setup crontab entry (fallback method)
setup_crontab() {
    log "Setting up crontab fallback..."
    
    local python_cmd="python3"
    for candidate in "$BOT_DIR/../.venv/bin/python3" "$BOT_DIR/.venv/bin/python3"; do
        if [[ -x "$candidate" ]]; then
            python_cmd="$candidate"
            break
        fi
    done

    local crontab_entry="@reboot sleep 45 && cd $BOT_DIR && $python_cmd main.py > $BOT_DIR/logs/cron.log 2>&1"
    
    # Check if crontab entry already exists
    if crontab -l 2>/dev/null | grep -q "main.py"; then
        log "Crontab entry already exists"
    else
        (crontab -l 2>/dev/null; echo "$crontab_entry") | crontab -
        log "Crontab entry added"
    fi
}

# Test the service
test_service() {
    log "Testing systemd service..."
    
    echo -e "\n${YELLOW}=== Service Status ===${NC}"
    systemctl --user status "$SERVICE_NAME" --no-pager || true
    
    echo -e "\n${YELLOW}=== Service Logs (last 10 lines) ===${NC}"
    journalctl --user -u "$SERVICE_NAME" -n 10 --no-pager || true
    
    echo -e "\n${YELLOW}=== Checking if bot process is running ===${NC}"
    if pgrep -f "python.*main.py" >/dev/null; then
        log "Bot process is running"
        ps aux | grep -v grep | grep "python.*main.py" || true
    else
        log_warning "No bot process found"
    fi
}

# Create backup of existing configuration
backup_existing_config() {
    log "Backing up existing configuration..."
    
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/backup_$backup_timestamp"
    
    mkdir -p "$backup_path"
    
    # Backup systemd service
    if [[ -f "$SYSTEMD_USER_DIR/$SERVICE_NAME" ]]; then
        cp "$SYSTEMD_USER_DIR/$SERVICE_NAME" "$backup_path/"
        log "Backed up systemd service file"
    fi
    
    # Backup autostart scripts
    if [[ -d "$AUTOSTART_DIR" ]]; then
        cp -r "$AUTOSTART_DIR" "$backup_path/autostart_backup"
        log "Backed up autostart scripts"
    fi
    
    log "Backup created: $backup_path"
}

# Final setup summary with verification
show_setup_summary() {
    echo -e "\n${GREEN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║           SETUP COMPLETE!                   ║"
    echo "║                                              ║"
    echo "║    C3NTR@L COMM@ND is ready to use!         ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    echo -e "\n${CYAN}📋 Setup Summary:${NC}"
    echo -e "  ${GREEN}✓${NC} Bot directory: $BOT_DIR"
    echo -e "  ${GREEN}✓${NC} Autostart scripts: $AUTOSTART_DIR"
    echo -e "  ${GREEN}✓${NC} Systemd service: $SERVICE_NAME"
    echo -e "  ${GREEN}✓${NC} Log directory: $BOT_DIR/logs"
    echo -e "  ${GREEN}✓${NC} Backup directory: $BACKUP_DIR"
    
    # Verify installation
    echo -e "\n${YELLOW}🔍 Verification:${NC}"
    if systemctl --user is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Systemd service: ENABLED for auto-start"
    else
        echo -e "  ${RED}✗${NC} Systemd service: NOT ENABLED"
    fi
    
    if systemctl --user is-active "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} Systemd service: CURRENTLY RUNNING"
    else
        echo -e "  ${YELLOW}⚠${NC} Systemd service: NOT RUNNING (may need manual start)"
    fi
    
    echo -e "\n${YELLOW}🚀 Quick Start:${NC}"
    echo -e "  ${CYAN}Start the bot now:${NC}"
    echo -e "    ${GREEN}systemctl --user start $SERVICE_NAME${NC}"
    echo -e "    ${GREEN}$BOT_DIR/manage_bot.sh start${NC}"
    
    echo -e "\n  ${CYAN}Check status:${NC}"
    echo -e "    ${GREEN}systemctl --user status $SERVICE_NAME${NC}"
    echo -e "    ${GREEN}$BOT_DIR/manage_bot.sh status${NC}"
    
    echo -e "\n  ${CYAN}View logs:${NC}"
    echo -e "    ${GREEN}journalctl --user -u $SERVICE_NAME -f${NC}"
    echo -e "    ${GREEN}$BOT_DIR/manage_bot.sh logs${NC}"
    
    echo -e "\n${BLUE}🔧 Management Options:${NC}"
    echo -e "  1. ${GREEN}Systemd Service${NC} (Recommended)"
    echo -e "     ${CYAN}systemctl --user <start|stop|restart> $SERVICE_NAME${NC}"
    echo -e "  2. ${GREEN}Management Helper${NC}"
    echo -e "     ${CYAN}$BOT_DIR/manage_bot.sh${NC}"
    
    echo -e "\n${YELLOW}📞 Auto-Start Methods Configured:${NC}"
    echo -e "  ${GREEN}✓${NC} Systemd user service (Primary)"
    echo -e "  ${GREEN}✓${NC} Desktop autostart (Backup)"
    echo -e "  ${GREEN}✓${NC} Crontab (Fallback)"
    
    echo -e "\n${GREEN}🎉 The bot will now start automatically on system boot!${NC}"
    echo -e "\n${YELLOW}⚠ IMPORTANT: Log out and log back in for auto-start to take full effect!${NC}"
}

# Main setup function
main() {
    log "Starting C3NTR@L COMM@ND auto-start setup..."
    
    # Run setup steps
    check_user
    check_bot_directory
    create_directories
    check_start_script
    check_virtual_environment
    backup_existing_config
    make_scripts_executable
    create_systemd_service
    install_systemd_service
    create_desktop_autostart
    setup_crontab
    test_service
    
    show_setup_summary
    
    log "Setup completed successfully!"
}

# Run main function
main "$@"