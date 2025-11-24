# C3NTR@L COMM@ND V1.1 🤖

**Advanced Telegram Bot with Auto-Start & Self-Healing Capabilities**

---

## 🚀 Overview

C3NTR@L COMM@ND is a comprehensive Telegram bot system that provides complete remote control of your Linux system. With advanced auto-start capabilities, self-healing features, and comprehensive monitoring, it ensures your bot is always available when you need it.

---

## ✨ Features

### 🤖 Core Bot Features
- **Remote System Control** - Complete control via Telegram
- **File Management** - Upload, download, and manage files remotely
- **Camera Access** - Take photos, record videos, surveillance mode
- **Network Tools** - Network diagnostics, speed tests, port scanning
- **System Control** - Shutdown, reboot, lock, message display
- **Security Tools** - Anti-theft, location tracking, emergency protocols
- **Task Scheduler** - Automated command scheduling

### 🛡️ Auto-Start & Reliability
- **Auto-Start on Boot** - Starts automatically when laptop powers on
- **Self-Healing** - Auto-restart on crashes (30-second recovery)
- **Multiple Fallbacks** - Systemd + Desktop Autostart + Crontab
- **Health Monitoring** - Continuous process monitoring
- **Resource Management** - CPU/Memory/Disk monitoring with alerts

### 🔧 Advanced Management
- **Virtual Environment** - Isolated Python environment
- **Comprehensive Logging** - Structured logs with rotation
- **Dual Notifications** - Telegram + Desktop notifications
- **Connection Tracking** - Online/offline state management
- **Performance Metrics** - Continuous system monitoring

---

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Telegram API  │◄──►│  C3NTR@L BOT    │◄──►│  Linux System   │
│                 │    │                  │    │                 │
│  - Commands     │    │  - Main Bot      │    │  - File System  │
│  - Notifications│    │  - Modules       │    │  - Camera       │
│  - Updates      │    │  - Auto-Start    │    │  - Network      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                │
                        ┌─────────────────┐
                        │  Systemd Service│
                        │                 │
                        │  - Auto-Start   │
                        │  - Monitoring   │
                        │  - Recovery     │
                        └─────────────────┘
```

---

## 📁 Project Structure

```
/home/imran/snap/C3NTR@L-COMM@ND-V1.1/
├── bot/
│   ├── main.py                 # Main bot dispatcher
│   ├── modules/               # Feature modules
│   │   ├── camera_tools.py
│   │   ├── file_manager.py
│   │   ├── network_tools.py
│   │   ├── system_control.py
│   │   ├── scheduler.py
│   │   └── security_tools.py
│   ├── autostart/            # Auto-start system
│   │   ├── start_bot.sh      # Advanced startup script
│   │   ├── setup_autostart.sh # Installation script
│   │   └── c3ntral-command.service
│   ├── manage_bot.sh         # Management helper
│   ├── logs/                 # Log directory
│   │   ├── autostart.log
│   │   ├── bot_console.log
│   │   └── bot_system.log
│   └── backups/              # Configuration backups
├── .venv/                    # Python virtual environment
└── config.json              # Bot configuration
```

---

## 🛠️ Installation & Setup

### Quick Start (Already Done)
```bash
cd /home/imran/snap/C3NTR@L-COMM@ND-V1.1/bot
./autostart/setup_autostart.sh
```

### Manual Setup (If Needed)
```bash
# Create directories
mkdir -p autostart logs backups

# Make scripts executable
chmod +x autostart/*.sh
chmod +x manage_bot.sh

# Setup auto-start
./autostart/setup_autostart.sh
```

---

## 🎮 Usage

### Bot Commands (Telegram)
```
/start - Check bot status
/help - Show all commands
/status - System status

📁 File Management:
/download <url> - Download file
/listfiles - List files
/sendfile <filename> - Send file
/deletefile <filename> - Delete file
/diskusage - Check disk space
/cleanup - Clean temporary files

📷 Camera Tools:
/photo - Take webcam photo
/record <seconds> - Record video
/surveillance - Motion detection
/screenshot - Desktop screenshot
/camerastatus - Camera status

🌐 Network Tools:
/ip - Get IP address
/wifi - WiFi information
/speedtest - Internet speed test
/ping <host> - Ping host
/vpn - VPN status
/netinfo - Network information
/ports - Open ports scan

⚙️ System Control:
/lock - Lock system
/unlock - Unlock system  
/shutdown - Shutdown system
/reboot - Reboot system
/sleep - Sleep mode
/msg <text> - Display message
/speak <text> - Text to speech

🛡️ Security Tools:
/antitheft - Enable anti-theft
/panic - Emergency panic mode
/lockdown - System lockdown
/wipe - Emergency data wipe
/geo - Location information
/alert - Configure alerts

⏰ Scheduler:
/schedule <time> <command> - Schedule command
/tasks - List scheduled tasks
/cancel <id> - Cancel task
```

### Management Commands (Local System)
```bash
# Using management helper
./manage_bot.sh status        # Check status
./manage_bot.sh start         # Start manually
./manage_bot.sh stop          # Stop manually
./manage_bot.sh restart       # Restart
./manage_bot.sh logs          # View logs
./manage_bot.sh diagnostics   # System diagnostics

# Using systemd directly
systemctl --user status c3ntral-command.service
systemctl --user restart c3ntral-command.service
systemctl --user stop c3ntral-command.service

# Using autostart script
./autostart/start_bot.sh status
./autostart/start_bot.sh start
./autostart/start_bot.sh monitor
```

---

## 🔧 Configuration

### config.json Structure
```json
{
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "admin_pin": "YOUR_PIN",
  "authorized_user_ids": [123456789],
  "security": {
    "session_timeout_minutes": 60,
    "encryption_key": "your-secret-key"
  },
  "paths": {
    "base_dir": "/home/imran/snap/C3NTR@L-COMM@ND-V1.1",
    "downloads_dir": "downloads",
    "logs_dir": "logs",
    "scripts_dir": "scripts"
  },
  "features": {
    "enable_camera": true,
    "enable_file_manager": true,
    "enable_network_tools": true,
    "enable_system_control": true,
    "enable_scheduler": true,
    "enable_security_tools": true,
    "offline_queue": true
  }
}
```

---

## 🚨 Emergency Features

### Panic Mode
```bash
/panic redalert  # Activates emergency protocols:
- Immediate system lockdown
- Enhanced evidence collection  
- Maximum alert escalation
- Continuous location tracking
```

### Anti-Theft Protection
```bash
/antitheft      # Enables:
- Motion detection
- Location tracking
- Network monitoring
- Automatic evidence collection
```

### Data Protection
```bash
/wipe confirm   # Emergency data wipe:
- Securely erases sensitive data
- Removes downloaded files
- Clears security evidence
- Cannot be undone!
```

---

## 📊 Monitoring & Logs

### Log Files
- `logs/autostart.log` - Auto-start system logs
- `logs/bot_console.log` - Bot output logs
- `logs/bot_system.log` - System events
- `logs/performance_metrics.log` - Performance data

### Viewing Logs
```bash
# Real-time logs
./manage_bot.sh logs
journalctl --user -u c3ntral-command.service -f

# Specific log files
tail -f logs/autostart.log
tail -f logs/bot_console.log
```

### System Diagnostics
```bash
./manage_bot.sh diagnostics
# Shows:
# - Bot status
# - Network connectivity
# - System resources
# - File status
# - Recent logs
```

---

## 🔄 Auto-Start System

### How It Works
1. **Primary**: Systemd user service (`c3ntral-command.service`)
2. **Backup**: Desktop autostart (GNOME/KDE)
3. **Fallback**: Crontab (@reboot)

### Auto-Recovery Features
- **Crash Detection** - Monitors bot process health
- **Auto-Restart** - Restarts within 30 seconds of crash
- **Resource Monitoring** - CPU/Memory/Disk thresholds
- **Connection Tracking** - Online/offline state management

### Manual Control
```bash
# Enable/disable auto-start
systemctl --user enable c3ntral-command.service
systemctl --user disable c3ntral-command.service

# Check auto-start status
systemctl --user is-enabled c3ntral-command.service
```

---

## 🛡️ Security Features

### Authentication
- **PIN-based access** for temporary sessions
- **Pre-authorized users** in config
- **Session timeout** (configurable)
- **Command authorization** for all features

### Data Protection
- **Encrypted configuration** for sensitive data
- **Secure file operations** with validation
- **Emergency wipe** capabilities
- **Log encryption** for sensitive information

### Network Security
- **Telegram API encryption**
- **Secure command transmission**
- **Network isolation** capabilities
- **VPN/proxy detection**

---

## 📈 Performance & Resources

### Resource Limits
- **Memory**: 512MB maximum
- **CPU**: 80% maximum quota
- **Auto-cleanup** of temporary files
- **Log rotation** to prevent disk filling

### Monitoring Thresholds
- **CPU**: 85% (warning), 95% (emergency)
- **Memory**: 90% (warning)
- **Disk**: 90% (warning)

### Optimization Features
- **Efficient polling** when idle
- **Smart resource usage** on battery
- **Background operation** with low priority
- **Automatic cleanup** of old logs

---

## 🔍 Troubleshooting

### Common Issues
```bash
# Bot not starting
./manage_bot.sh diagnostics
journalctl --user -u c3ntral-command.service --no-pager

# Permission issues
chmod +x autostart/*.sh
chmod +x manage_bot.sh

# Virtual environment issues
source ../.venv/bin/activate
pip install -r requirements.txt
```

### Log Locations
- Systemd logs: `journalctl --user -u c3ntral-command.service`
- Application logs: `logs/` directory
- Auto-start logs: `logs/autostart.log`

### Recovery Procedures
```bash
# Full system reset
./autostart/setup_autostart.sh

# Manual recovery
systemctl --user daemon-reload
systemctl --user reset-failed c3ntral-command.service
systemctl --user start c3ntral-command.service
```

---

## 📞 Support & Maintenance

### Regular Maintenance
```bash
# Cleanup system
./manage_bot.sh cleanup

# Update dependencies
source ../.venv/bin/activate
pip install --upgrade -r requirements.txt

# Backup configuration
cp config.json config.backup.json
```

### Monitoring Health
```bash
# Daily check
./manage_bot.sh status
./manage_bot.sh diagnostics

# Log review
tail -20 logs/autostart.log
```

### Getting Help
1. Check logs: `./manage_bot.sh logs`
2. Run diagnostics: `./manage_bot.sh diagnostics`
3. Review systemd: `systemctl --user status c3ntral-command.service`

---

## 🎯 Key Benefits

### 🕒 Always Available
- Starts automatically on boot
- Survives crashes with auto-restart
- Works offline (queues commands)
- Reconnects automatically

### 🛡️ Enterprise Reliability
- Systemd service management
- Comprehensive monitoring
- Resource limits and protection
- Professional logging

### 🔧 Easy Management
- Simple start/stop/status commands
- Comprehensive diagnostics
- Multiple control methods
- Clear status indicators

### ⚡ Advanced Features
- Virtual environment isolation
- Dual notification system
- Performance optimization
- Security protocols

---

## 🚀 Future Enhancements

- [ ] Web dashboard for management
- [ ] Mobile app companion
- [ ] Advanced analytics
- [ ] Plugin system for extensions
- [ ] Cloud backup integration
- [ ] Multi-user support

---

## 📄 License & Credits

**C3NTR@L COMM@ND V1.1** - Advanced Telegram Bot System  
*Built for reliability and continuous operation*

---
**Your bot is now enterprise-ready with professional auto-start capabilities!**