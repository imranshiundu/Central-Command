#!/bin/bash

# C3NTR@L COMM@ND - Bot Management Helper
# Works from any clone location; no hardcoded paths.

BOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
    echo "║           C3NTR@L COMM@ND                    ║"
    echo "║           Management Console                 ║"
    echo "╚══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# True if a systemd user session is available
has_systemd() {
    systemctl --user is-system-running >/dev/null 2>&1 \
        || [[ "$(systemctl --user is-system-running 2>&1)" == "degraded" ]]
}

show_status() {
    echo -e "\n${YELLOW}=== Bot Status ===${NC}"

    if has_systemd; then
        if systemctl --user is-active "$SERVICE_NAME" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Systemd service: ACTIVE${NC}"
        elif systemctl --user is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
            echo -e "${YELLOW}⚠ Systemd service: ENABLED but INACTIVE${NC}"
        else
            echo -e "${RED}✗ Systemd service: DISABLED or NOT FOUND${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No systemd user session (use '$0 run' to start directly)${NC}"
    fi

    if pgrep -f "python.*main.py" >/dev/null; then
        echo -e "${GREEN}✓ Bot process: RUNNING${NC}"
        ps aux | grep -v grep | grep "python.*main.py" | while read -r line; do
            echo -e "  ${BLUE}${line}${NC}"
        done
    else
        echo -e "${RED}✗ Bot process: NOT RUNNING${NC}"
    fi

    if curl -s --connect-timeout 5 https://www.google.com >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Internet: CONNECTED${NC}"
    else
        echo -e "${YELLOW}⚠ Internet: DISCONNECTED${NC}"
    fi

    if [[ -f "$BOT_DIR/config.json" ]]; then
        echo -e "${GREEN}✓ Config: FOUND${NC}"
    else
        echo -e "${RED}✗ Config: MISSING (copy config.example.json -> config.json)${NC}"
    fi
}

show_diagnostics() {
    show_header
    echo -e "${CYAN}🤖 System Diagnostics${NC}"
    echo "=========================================="

    show_status

    echo -e "\n${YELLOW}=== Environment ===${NC}"
    echo "  Bot dir:     $BOT_DIR"
    echo "  Python:      $(python3 --version 2>&1)"
    if [[ -f "$BOT_DIR/../../.venv/bin/python3" ]]; then
        echo -e "  ${GREEN}✓ Venv: found${NC}"
    else
        echo -e "  ${YELLOW}⚠ Venv: not found (system python will be used)${NC}"
    fi

    echo -e "\n${YELLOW}=== Python dependencies ===${NC}"
    python3 - <<'PYEOF'
import importlib.util
for pkg in ('telegram', 'psutil', 'requests'):
    ok = importlib.util.find_spec(pkg) is not None
    print(f"  {'✓' if ok else '✗'} {pkg}{'' if ok else '  (MISSING - pip install -r requirements.txt)'}")
PYEOF

    echo -e "\n${YELLOW}=== Auto-Start ===${NC}"
    if has_systemd && systemctl --user is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ Systemd service: ENABLED${NC}"
    else
        echo -e "${RED}✗ Systemd service: NOT ENABLED${NC}"
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

    echo -e "\n${YELLOW}=== Recent console log ===${NC}"
    tail -5 "$BOT_DIR/logs/bot_console.log" 2>/dev/null || echo "  (no console log yet)"
}

# Direct launch without systemd (works everywhere)
run_bot() {
    cd "$BOT_DIR" || return 1
    local venv_python="$BOT_DIR/../../.venv/bin/python3"
    if [[ -x "$venv_python" ]]; then
        exec "$venv_python" main.py
    else
        exec python3 main.py
    fi
}

start_service() {
    if has_systemd; then
        systemctl --user start "$SERVICE_NAME"
    else
        echo -e "${YELLOW}No systemd user session; starting bot directly (Ctrl+C stops it)${NC}"
        run_bot
    fi
}

case "${1:-}" in
    start)    start_service ;;
    stop)
        if has_systemd; then systemctl --user stop "$SERVICE_NAME"; fi
        pkill -f "python.*main.py" 2>/dev/null || true
        ;;
    restart)
        if has_systemd; then systemctl --user restart "$SERVICE_NAME"; else start_service; fi
        ;;
    run)      run_bot ;;
    status)
        show_header
        show_status
        if has_systemd; then
            echo -e "\n${YELLOW}=== Service Details ===${NC}"
            systemctl --user status "$SERVICE_NAME" --no-pager || true
        fi
        ;;
    diagnostics|diag) show_diagnostics ;;
    logs)
        if has_systemd; then
            journalctl --user -u "$SERVICE_NAME" -f
        else
            tail -f "$BOT_DIR/logs/bot_console.log" 2>/dev/null
        fi
        ;;
    enable)
        if has_systemd; then systemctl --user enable "$SERVICE_NAME"; fi
        ;;
    disable)
        if has_systemd; then systemctl --user disable "$SERVICE_NAME"; fi
        ;;
    help|--help|-h|"")
        show_header
        show_status
        echo -e "\n${GREEN}Commands:${NC}"
        echo "  start        - Start bot (systemd, or direct if no systemd session)"
        echo "  stop         - Stop bot"
        echo "  restart      - Restart bot"
        echo "  run          - Run bot directly in this terminal"
        echo "  status       - Detailed status"
        echo "  diagnostics  - Full system diagnostics"
        echo "  logs         - Follow logs"
        echo "  enable       - Enable auto-start on boot"
        echo "  disable      - Disable auto-start on boot"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        "$0" help
        exit 1
        ;;
esac
