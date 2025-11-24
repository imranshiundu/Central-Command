#!/bin/bash

# C3NTR@L COMM@ND - Bot Management Helper
# Easy-to-use management interface

BOT_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1/bot"
SERVICE_NAME="c3ntral-command.service"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

show_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════╗"
    echo "║           C3NTR@L COMM@ND V1.1              ║"
    echo "║           Management Console                ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_status() {
    echo -e "\n${YELLOW}=== System Status ===${NC}"
    
    # Systemd status
    if systemctl --user is-active "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Systemd service: ACTIVE${NC}"
    elif systemctl --user is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Systemd service: ENABLED but INACTIVE${NC}"
    else
        echo -e "${RED}✗ Systemd service: DISABLED or NOT FOUND${NC}"
    fi
    
    # Process status
    if pgrep -f "python.*main.py" >/dev/null; then
        echo -e "${GREEN}✓ Bot process: RUNNING${NC}"
        echo -e "  Processes:"
        ps aux | grep -v grep | grep "python.*main.py" | while read line; do
            echo -e "  ${BLUE}  $line${NC}"
        done
    else
        echo -e "${RED}✗ Bot process: NOT RUNNING${NC}"
    fi
    
    # Network check
    if curl -s --connect-timeout 5 https://www.google.com >/dev/null; then
        echo -e "${GREEN}✓ Internet: CONNECTED${NC}"
    else
        echo -e "${YELLOW}⚠ Internet: DISCONNECTED${NC}"
    fi
    
    # Auto-start methods
    echo -e "\n${YELLOW}=== Auto-Start Methods ===${NC}"
    if systemctl --user is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Systemd service: ENABLED${NC}"
    else
        echo -e "${RED}✗ Systemd service: DISABLED${NC}"
    fi
    
    if [[ -f "$HOME/.config/autostart/c3ntral-command.desktop" ]]; then
        echo -e "${GREEN}✓ Desktop autostart: CONFIGURED${NC}"
    else
        echo -e "${RED}✗ Desktop autostart: NOT CONFIGURED${NC}"
    fi
    
    if crontab -l 2>/dev/null | grep -q "main.py"; then
        echo -e "${GREEN}✓ Crontab: CONFIGURED${NC}"
    else
        echo -e "${RED}✗ Crontab: NOT CONFIGURED${NC}"
    fi
}

case "${1:-}" in
    start)
        echo -e "${GREEN}Starting bot via systemd...${NC}"
        systemctl --user start "$SERVICE_NAME"
        ;;
    stop)
        echo -e "${YELLOW}Stopping bot...${NC}"
        systemctl --user stop "$SERVICE_NAME"
        # Also kill any stray processes
        pkill -f "python.*main.py" 2>/dev/null || true
        ;;
    restart)
        echo -e "${BLUE}Restarting bot...${NC}"
        systemctl --user restart "$SERVICE_NAME"
        ;;
    status)
        show_header
        show_status
        echo -e "\n${YELLOW}=== Service Details ===${NC}"
        systemctl --user status "$SERVICE_NAME" --no-pager || true
        ;;
    logs)
        echo -e "${CYAN}Showing service logs (Ctrl+C to exit)...${NC}"
        journalctl --user -u "$SERVICE_NAME" -f
        ;;
    enable)
        echo -e "${GREEN}Enabling auto-start...${NC}"
        systemctl --user enable "$SERVICE_NAME"
        ;;
    disable)
        echo -e "${YELLOW}Disabling auto-start...${NC}"
        systemctl --user disable "$SERVICE_NAME"
        ;;
    service-start)
        echo -e "${GREEN}Starting systemd service...${NC}"
        systemctl --user start "$SERVICE_NAME"
        ;;
    service-stop)
        echo -e "${YELLOW}Stopping systemd service...${NC}"
        systemctl --user stop "$SERVICE_NAME"
        ;;
    service-status)
        systemctl --user status "$SERVICE_NAME"
        ;;
    service-restart)
        echo -e "${BLUE}Restarting systemd service...${NC}"
        systemctl --user restart "$SERVICE_NAME"
        ;;
    service-logs)
        echo -e "${CYAN}Showing service logs (Ctrl+C to exit)...${NC}"
        journalctl --user -u "$SERVICE_NAME" -f
        ;;
    *)
        show_header
        show_status
        echo -e "\n${GREEN}Available Commands:${NC}"
        echo "  start           - Start bot via systemd"
        echo "  stop            - Stop bot"
        echo "  restart         - Restart bot"
        echo "  status          - Show detailed status"
        echo "  logs            - Show service logs"
        echo "  enable          - Enable auto-start"
        echo "  disable         - Disable auto-start"
        echo ""
        echo "${YELLOW}Systemd Service Commands:${NC}"
        echo "  service-start   - Start systemd service"
        echo "  service-stop    - Stop systemd service"
        echo "  service-status  - Show service status"
        echo "  service-restart - Restart systemd service"
        echo "  service-logs    - Show service logs"
        echo ""
        echo "${CYAN}Examples:${NC}"
        echo "  $0 start        # Start bot"
        echo "  $0 status       # Check status"
        echo "  $0 logs         # View logs"
        ;;
esac
