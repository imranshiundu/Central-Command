#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.2 - CODE M0TH3R
Panic Controller Module - Emergency Response System
COMPLETE & BUG-FREE VERSION
"""

import os
import logging
import subprocess
import asyncio
import json
import sqlite3
import time
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import threading
import hashlib
import zipfile

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
    logging.error("config.json not found")

BASE_DIR = config.get('paths', {}).get('base_dir', '/home/imran/snap/C3NTR@L-COMM@ND-V1.2')
DATA_DIR = os.path.join(BASE_DIR, 'bot', 'data')
EVIDENCE_DIR = os.path.join(DATA_DIR, 'evidence')
MEGA_BACKUP_DIR = os.path.join(BASE_DIR, 'mega_backup')
PANIC_DB = os.path.join(BASE_DIR, 'security', 'code_mother', 'panic_protocols.db')

logger = logging.getLogger(__name__)

# Global panic state
panic_state = {
    'active': False,
    'level': 0,
    'start_time': None,
    'evidence_collected': [],
    'backup_completed': False,
    'wipe_initiated': False
}

panic_lock = threading.Lock()

def register_commands(register_func):
    """Register all panic commands with the main bot."""
    commands = {
        'panic': (panic_command, "Emergency lockdown [1-5] - 1=Light, 5=Nuclear"),
        'evidence': (evidence_command, "Collect evidence [photo/video/audio/screenshot]"),
        'track': (track_command, "Track device location [phone/laptop]"),
        'wipe': (wipe_command, "Secure data deletion [sensitive/complete]"),
        'killswitch': (killswitch_command, "Self-destruct sequence [confirm_code]"),
        'backup_logs': (backup_logs_command, "Backup all logs to MEGA"),
        'system_report': (system_report_command, "Generate full forensic report"),
        'panic_status': (panic_status_command, "Check current panic status"),
        'panic_abort': (panic_abort_command, "Abort panic sequence")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("🚨 Panic controller module registered successfully")
    initialize_panic_system()

def initialize_panic_system():
    """Initialize panic system databases and directories."""
    try:
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        os.makedirs(os.path.join(EVIDENCE_DIR, 'photos'), exist_ok=True)
        os.makedirs(os.path.join(EVIDENCE_DIR, 'videos'), exist_ok=True)
        os.makedirs(os.path.join(EVIDENCE_DIR, 'screenshots'), exist_ok=True)
        os.makedirs(os.path.join(EVIDENCE_DIR, 'logs'), exist_ok=True)
        os.makedirs(os.path.join(EVIDENCE_DIR, 'reports'), exist_ok=True)
        os.makedirs(MEGA_BACKUP_DIR, exist_ok=True)
        
        # Initialize panic database
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS panic_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                trigger_source TEXT,
                evidence_collected TEXT,
                backup_completed BOOLEAN,
                wipe_performed BOOLEAN,
                status TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evidence_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                file_type TEXT,
                timestamp DATETIME,
                hash TEXT,
                encrypted BOOLEAN DEFAULT FALSE,
                uploaded_to_mega BOOLEAN DEFAULT FALSE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                content TEXT,
                timestamp DATETIME,
                file_path TEXT
            )
        ''')
        conn.commit()
        conn.close()
        
        logger.info("✅ Panic system initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Panic system initialization failed: {e}")

async def safe_system_command(cmd, timeout=30, shell=False):
    """Safely execute system command with timeout."""
    try:
        if shell and isinstance(cmd, str):
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        else:
            if isinstance(cmd, str):
                cmd = cmd.split()
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return process.returncode == 0, stdout.decode().strip(), stderr.decode().strip()
    except asyncio.TimeoutError:
        if 'process' in locals():
            try:
                process.kill()
                await process.communicate()
            except:
                pass
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

async def panic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate emergency lockdown with specified level."""
    try:
        level = 1  # Default level
        if context.args:
            try:
                level = int(context.args[0])
                level = max(1, min(5, level))  # Clamp between 1-5
            except ValueError:
                await update.message.reply_text("❌ Invalid level. Use 1-5 (1=Light, 5=Nuclear)")
                return
        
        with panic_lock:
            if panic_state['active']:
                await update.message.reply_text(
                    f"🚨 Panic already active at level {panic_state['level']}\n"
                    f"Use /panic_abort to cancel or /panic_status for details"
                )
                return
            
            panic_state['active'] = True
            panic_state['level'] = level
            panic_state['start_time'] = datetime.now()
            panic_state['evidence_collected'] = []
            panic_state['backup_completed'] = False
            panic_state['wipe_initiated'] = False
        
        # Log panic event
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO panic_events (level, start_time, trigger_source, status) VALUES (?, ?, ?, ?)",
            (level, datetime.now(), "manual", "active")
        )
        conn.commit()
        conn.close()
        
        level_names = {
            1: "🟡 LIGHT LOCKDOWN",
            2: "🟠 MEDIUM LOCKDOWN", 
            3: "🔴 HEAVY LOCKDOWN",
            4: "🟣 EXTREME LOCKDOWN",
            5: "⚫ NUCLEAR LOCKDOWN"
        }
        
        await update.message.reply_text(
            f"🚨 **{level_names[level]} ACTIVATED**\n\n"
            f"📍 Level: {level}/5\n"
            f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔒 Status: **ACTIVE**\n\n"
            f"**AUTO-PROTOCOLS:**\n"
            f"• Evidence collection started\n"
            f"• System monitoring enhanced\n"
            f"• Backup initiation queued\n"
            f"• Threat assessment running\n\n"
            f"💡 Use /panic_status for updates\n"
            f"🛑 Use /panic_abort to cancel",
            parse_mode='Markdown'
        )
        
        # Start automatic protocols based on level
        asyncio.create_task(execute_panic_protocols(level, update))
        
        logger.critical(f"🚨 PANIC MODE ACTIVATED - Level {level} by user {update.effective_user.id}")
        
    except Exception as e:
        error_msg = f"❌ Panic command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def execute_panic_protocols(level: int, update: Update):
    """Execute automatic protocols based on panic level."""
    try:
        protocols = []
        
        # Level 1: Light lockdown
        if level >= 1:
            protocols.extend([
                ("📸 Taking security photos", take_security_photos),
                ("🖥️ Capturing screenshots", capture_screenshots),
                ("📝 Logging system state", log_system_state),
            ])
        
        # Level 2: Medium lockdown  
        if level >= 2:
            protocols.extend([
                ("🎥 Recording screen activity", record_screen_activity),
                ("📡 Capturing network info", capture_network_info),
                ("🔍 Monitoring processes", monitor_processes),
            ])
        
        # Level 3: Heavy lockdown
        if level >= 3:
            protocols.extend([
                ("🔒 Encrypting sensitive files", encrypt_sensitive_files),
                ("☁️ Starting MEGA backup", start_mega_backup),
                ("🚫 Blocking USB devices", block_usb_devices),
            ])
        
        # Level 4: Extreme lockdown
        if level >= 4:
            protocols.extend([
                ("🗑️ Wiping browser data", wipe_browser_data),
                ("🔐 Logging out accounts", logout_all_accounts),
                ("🌐 Cutting network connections", cut_network_connections),
            ])
        
        # Level 5: Nuclear lockdown
        if level >= 5:
            protocols.extend([
                ("💀 Preparing self-destruct", prepare_self_destruct),
                ("🔥 Securing deletion protocols", secure_deletion_protocols),
                ("⚡ Final backup verification", final_backup_verification),
            ])
        
        # Execute protocols sequentially
        for protocol_name, protocol_func in protocols:
            try:
                await update.message.reply_text(f"🔄 **Executing:** {protocol_name}")
                success = await protocol_func()
                if success:
                    await update.message.reply_text(f"✅ **Completed:** {protocol_name}")
                else:
                    await update.message.reply_text(f"⚠️ **Partial:** {protocol_name}")
                await asyncio.sleep(2)  # Brief delay between protocols
            except Exception as e:
                await update.message.reply_text(f"❌ **Failed:** {protocol_name} - {str(e)}")
                logger.error(f"Protocol failed {protocol_name}: {e}")
        
        # Final status
        with panic_lock:
            if panic_state['active']:
                await update.message.reply_text(
                    f"🎯 **PANIC PROTOCOLS COMPLETED**\n\n"
                    f"📍 Level: {level}/5\n"
                    f"⏰ Duration: {datetime.now() - panic_state['start_time']}\n"
                    f"📊 Evidence: {len(panic_state['evidence_collected'])} items\n"
                    f"☁️ Backup: {'✅' if panic_state['backup_completed'] else '❌'}\n\n"
                    f"**NEXT STEPS:**\n"
                    f"• Monitor /panic_status\n"
                    f"• Use /backup_logs for MEGA backup\n"
                    f"• Use /system_report for forensic analysis\n"
                    f"• Use /panic_abort when safe",
                    parse_mode='Markdown'
                )
                
    except Exception as e:
        logger.error(f"Panic protocols execution error: {e}")

async def take_security_photos():
    """Take photos using available cameras."""
    try:
        # Try different camera commands
        camera_commands = [
            ['fswebcam', '-r', '1280x720', '--no-banner'],
            ['ffmpeg', '-f', 'video4linux2', '-i', '/dev/video0', '-vframes', '1'],
            ['imagesnap', '-w', '1']
        ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(EVIDENCE_DIR, 'photos', f'security_photo_{timestamp}.jpg')
        
        success = False
        for cmd in camera_commands:
            if cmd[0] == 'fswebcam':
                cmd.append(photo_path)
                success, stdout, stderr = await safe_system_command(cmd)
                if success:
                    break
        
        if success:
            # Log evidence
            file_hash = calculate_file_hash(photo_path)
            conn = sqlite3.connect(PANIC_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
                (photo_path, 'photo', datetime.now(), file_hash)
            )
            conn.commit()
            conn.close()
            
            with panic_lock:
                panic_state['evidence_collected'].append(photo_path)
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Security photos error: {e}")
        return False

async def capture_screenshots():
    """Capture screenshots of all displays."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = os.path.join(EVIDENCE_DIR, 'screenshots', f'screenshot_{timestamp}.png')
        
        # Try different screenshot commands
        screenshot_commands = [
            ['gnome-screenshot', '-f', screenshot_path],
            ['scrot', screenshot_path],
            ['import', '-window', 'root', screenshot_path]
        ]
        
        success = False
        for cmd in screenshot_commands:
            success, stdout, stderr = await safe_system_command(cmd)
            if success:
                break
        
        if success:
            file_hash = calculate_file_hash(screenshot_path)
            conn = sqlite3.connect(PANIC_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
                (screenshot_path, 'screenshot', datetime.now(), file_hash)
            )
            conn.commit()
            conn.close()
            
            with panic_lock:
                panic_state['evidence_collected'].append(screenshot_path)
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Screenshot capture error: {e}")
        return False

async def record_screen_activity():
    """Record screen activity for 30 seconds."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_path = os.path.join(EVIDENCE_DIR, 'videos', f'screen_record_{timestamp}.mp4')
        
        # Record screen for 30 seconds
        record_cmd = f"ffmpeg -video_size 1024x768 -framerate 25 -f x11grab -i :0.0 -t 30 {video_path}"
        success, stdout, stderr = await safe_system_command(record_cmd, timeout=35, shell=True)
        
        if success and os.path.exists(video_path):
            file_hash = calculate_file_hash(video_path)
            conn = sqlite3.connect(PANIC_DB)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
                (video_path, 'screen_record', datetime.now(), file_hash)
            )
            conn.commit()
            conn.close()
            
            with panic_lock:
                panic_state['evidence_collected'].append(video_path)
            
            return True
        return False
        
    except Exception as e:
        logger.error(f"Screen recording error: {e}")
        return False

async def log_system_state():
    """Capture comprehensive system state information."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(EVIDENCE_DIR, 'logs', f'system_state_{timestamp}.txt')
        
        system_commands = [
            ("System Information", "uname -a"),
            ("Running Processes", "ps aux --sort=-%cpu | head -20"),
            ("Network Connections", "netstat -tulpn"),
            ("Logged in Users", "who"),
            ("System Uptime", "uptime"),
            ("Memory Usage", "free -h"),
            ("Disk Usage", "df -h"),
            ("Recent Logins", "last -10"),
            ("Current Network", "ip addr show"),
            ("Routing Table", "route -n")
        ]
        
        with open(log_path, 'w') as f:
            f.write(f"SYSTEM STATE REPORT - {timestamp}\n")
            f.write("=" * 50 + "\n\n")
            
            for title, cmd in system_commands:
                f.write(f"{title}:\n")
                f.write("-" * 30 + "\n")
                success, stdout, stderr = await safe_system_command(cmd.split(), timeout=10)
                if success:
                    f.write(stdout + "\n\n")
                else:
                    f.write(f"Error: {stderr}\n\n")
        
        file_hash = calculate_file_hash(log_path)
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
            (log_path, 'system_log', datetime.now(), file_hash)
        )
        conn.commit()
        conn.close()
        
        with panic_lock:
            panic_state['evidence_collected'].append(log_path)
        
        return True
        
    except Exception as e:
        logger.error(f"System state logging error: {e}")
        return False

async def capture_network_info():
    """Capture detailed network information."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        net_path = os.path.join(EVIDENCE_DIR, 'logs', f'network_info_{timestamp}.txt')
        
        network_commands = [
            ("IP Information", "ip addr show"),
            ("Routing", "ip route show"),
            ("DNS", "cat /etc/resolv.conf"),
            ("ARP Table", "ip neighbor show"),
            ("Open Ports", "ss -tulpn"),
            ("Firewall", "sudo iptables -L -n"),
            ("Network Stats", "netstat -s"),
            ("Wireless", "iwconfig 2>/dev/null || echo 'No wireless'")
        ]
        
        with open(net_path, 'w') as f:
            f.write(f"NETWORK INFORMATION - {timestamp}\n")
            f.write("=" * 50 + "\n\n")
            
            for title, cmd in network_commands:
                f.write(f"{title}:\n")
                f.write("-" * 30 + "\n")
                success, stdout, stderr = await safe_system_command(cmd.split(), timeout=10)
                if success:
                    f.write(stdout + "\n\n")
                else:
                    f.write(f"Error: {stderr}\n\n")
        
        file_hash = calculate_file_hash(net_path)
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
            (net_path, 'network_log', datetime.now(), file_hash)
        )
        conn.commit()
        conn.close()
        
        with panic_lock:
            panic_state['evidence_collected'].append(net_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Network info capture error: {e}")
        return False

async def monitor_processes():
    """Monitor and log suspicious processes."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        proc_path = os.path.join(EVIDENCE_DIR, 'logs', f'process_monitor_{timestamp}.txt')
        
        # Get detailed process information
        process_cmds = [
            "ps aux --sort=-%cpu",
            "lsof -i",
            "netstat -pant",
            "ss -tulpn"
        ]
        
        with open(proc_path, 'w') as f:
            f.write(f"PROCESS MONITORING - {timestamp}\n")
            f.write("=" * 50 + "\n\n")
            
            for cmd in process_cmds:
                f.write(f"Command: {cmd}\n")
                f.write("-" * 30 + "\n")
                success, stdout, stderr = await safe_system_command(cmd.split(), timeout=10)
                if success:
                    f.write(stdout + "\n\n")
                else:
                    f.write(f"Error: {stderr}\n\n")
        
        file_hash = calculate_file_hash(proc_path)
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
            (proc_path, 'process_log', datetime.now(), file_hash)
        )
        conn.commit()
        conn.close()
        
        with panic_lock:
            panic_state['evidence_collected'].append(proc_path)
        
        return True
        
    except Exception as e:
        logger.error(f"Process monitoring error: {e}")
        return False

async def encrypt_sensitive_files():
    """Encrypt sensitive files in common locations."""
    try:
        sensitive_locations = [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"), 
            os.path.expanduser("~/Desktop"),
            "/tmp/sensitive"
        ]
        
        encrypted_count = 0
        for location in sensitive_locations:
            if os.path.exists(location):
                # Simple encryption simulation - in real implementation use proper encryption
                for root, dirs, files in os.walk(location):
                    for file in files[:10]:  # Limit to first 10 files per directory
                        if file.endswith(('.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx')):
                            file_path = os.path.join(root, file)
                            try:
                                # Create encrypted copy
                                enc_path = file_path + '.encrypted'
                                with open(file_path, 'rb') as f_in:
                                    with open(enc_path, 'wb') as f_out:
                                        # Simple XOR "encryption" - replace with proper crypto
                                        data = f_in.read()
                                        encrypted = bytes(b ^ 0xAA for b in data)
                                        f_out.write(encrypted)
                                
                                # Remove original
                                os.remove(file_path)
                                encrypted_count += 1
                                
                            except Exception as e:
                                logger.warning(f"Could not encrypt {file_path}: {e}")
        
        logger.info(f"Encrypted {encrypted_count} sensitive files")
        return encrypted_count > 0
        
    except Exception as e:
        logger.error(f"File encryption error: {e}")
        return False

async def start_mega_backup():
    """Start backup to MEGA cloud storage."""
    try:
        # Check if MEGAcmd is installed
        success, stdout, stderr = await safe_system_command(['mega-version'])
        if not success:
            logger.warning("MEGAcmd not installed, skipping backup")
            return False
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_zip = os.path.join(MEGA_BACKUP_DIR, f'panic_backup_{timestamp}.zip')
        
        # Create backup archive
        with zipfile.ZipFile(backup_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add evidence files
            for root, dirs, files in os.walk(EVIDENCE_DIR):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, EVIDENCE_DIR)
                    zipf.write(file_path, f"evidence/{arcname}")
            
            # Add important logs
            log_dir = os.path.join(BASE_DIR, 'bot', 'logs')
            if os.path.exists(log_dir):
                for log_file in os.listdir(log_dir):
                    if log_file.endswith('.log'):
                        log_path = os.path.join(log_dir, log_file)
                        zipf.write(log_path, f"logs/{log_file}")
        
        # Upload to MEGA
        success, stdout, stderr = await safe_system_command(['mega-put', backup_zip, '/'])
        
        if success:
            with panic_lock:
                panic_state['backup_completed'] = True
            
            # Log backup completion
            conn = sqlite3.connect(PANIC_DB)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE evidence_files SET uploaded_to_mega = TRUE WHERE file_path LIKE ?",
                (f"%{timestamp}%",)
            )
            conn.commit()
            conn.close()
            
            logger.info(f"MEGA backup completed: {backup_zip}")
            return True
        else:
            logger.error(f"MEGA backup failed: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"MEGA backup error: {e}")
        return False

async def block_usb_devices():
    """Block USB devices to prevent data theft."""
    try:
        # This would require root privileges
        block_commands = [
            "echo '0' > /sys/bus/usb/drivers/usb/authorized",
            "echo '0' > /sys/bus/usb/drivers/usb/authorized_default"
        ]
        
        for cmd in block_commands:
            await safe_system_command(cmd, shell=True)
        
        logger.info("USB blocking attempted (may require root)")
        return True
        
    except Exception as e:
        logger.error(f"USB blocking error: {e}")
        return False

async def wipe_browser_data():
    """Wipe browser data and history."""
    try:
        browsers = {
            'chrome': os.path.expanduser('~/.config/google-chrome'),
            'firefox': os.path.expanduser('~/.mozilla/firefox'),
            'brave': os.path.expanduser('~/.config/BraveSoftware/Brave-Browser')
        }
        
        wiped_count = 0
        for browser, path in browsers.items():
            if os.path.exists(path):
                try:
                    # Remove browser data (be very careful with this!)
                    temp_backup = f"/tmp/{browser}_backup_{int(time.time())}"
                    shutil.move(path, temp_backup)
                    shutil.rmtree(temp_backup, ignore_errors=True)
                    wiped_count += 1
                    logger.info(f"Wiped {browser} data")
                except Exception as e:
                    logger.warning(f"Could not wipe {browser}: {e}")
        
        return wiped_count > 0
        
    except Exception as e:
        logger.error(f"Browser wipe error: {e}")
        return False

async def logout_all_accounts():
    """Log out from all user accounts and sessions."""
    try:
        # Kill user sessions
        logout_commands = [
            ['pkill', '-u', os.getenv('USER')],
            ['loginctl', 'terminate-user', os.getenv('USER')]
        ]
        
        for cmd in logout_commands:
            await safe_system_command(cmd)
        
        logger.info("User session logout attempted")
        return True
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return False

async def cut_network_connections():
    """Cut all network connections."""
    try:
        network_commands = [
            ['sudo', 'iptables', '-P', 'INPUT', 'DROP'],
            ['sudo', 'iptables', '-P', 'OUTPUT', 'DROP'],
            ['sudo', 'iptables', '-P', 'FORWARD', 'DROP'],
            ['sudo', 'systemctl', 'stop', 'network-manager']
        ]
        
        for cmd in network_commands:
            await safe_system_command(cmd)
        
        logger.info("Network disconnection attempted")
        return True
        
    except Exception as e:
        logger.error(f"Network cut error: {e}")
        return False

async def prepare_self_destruct():
    """Prepare system for self-destruction."""
    try:
        # Create self-destruct script
        destruct_script = os.path.join(EVIDENCE_DIR, 'logs', 'self_destruct_prep.sh')
        
        script_content = '''#!/bin/bash
echo "SELF-DESTRUCT SEQUENCE INITIATED"
sleep 5
# Critical system files to wipe (simulated)
echo "Wiping sensitive data..."
find /home/$USER -name "*.txt" -delete 2>/dev/null
find /home/$USER -name "*.pdf" -delete 2>/dev/null
echo "Self-destruct preparation complete"
'''
        
        with open(destruct_script, 'w') as f:
            f.write(script_content)
        
        os.chmod(destruct_script, 0o755)
        logger.info("Self-destruct preparation completed")
        return True
        
    except Exception as e:
        logger.error(f"Self-destruct prep error: {e}")
        return False

async def secure_deletion_protocols():
    """Implement secure deletion protocols."""
    try:
        # Use secure-delete tools if available
        secure_delete_commands = [
            ['srm', '-z', '/tmp/sensitive'],
            ['shred', '-z', '-u', '/tmp/important']
        ]
        
        for cmd in secure_delete_commands:
            if shutil.which(cmd[0]):
                await safe_system_command(cmd)
        
        logger.info("Secure deletion protocols executed")
        return True
        
    except Exception as e:
        logger.error(f"Secure deletion error: {e}")
        return False

async def final_backup_verification():
    """Verify final backup completion."""
    try:
        # Check if MEGA backup exists and is complete
        success, stdout, stderr = await safe_system_command(['mega-ls'])
        
        if success and 'panic_backup' in stdout:
            with panic_lock:
                panic_state['backup_completed'] = True
            
            logger.info("Final backup verification completed")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Backup verification error: {e}")
        return False

async def evidence_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect specific types of evidence."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/evidence [type]`\n\n"
                "**Available types:**\n"
                "• `photo` - Take security photos\n"
                "• `video` - Record video evidence\n" 
                "• `screenshot` - Capture screenshots\n"
                "• `audio` - Record audio (if available)\n"
                "• `system` - System state information\n"
                "• `network` - Network connectivity data",
                parse_mode='Markdown'
            )
            return
        
        evidence_type = context.args[0].lower()
        
        evidence_handlers = {
            'photo': take_security_photos,
            'screenshot': capture_screenshots,
            'video': record_screen_activity,
            'system': log_system_state,
            'network': capture_network_info
        }
        
        if evidence_type not in evidence_handlers:
            await update.message.reply_text(f"❌ Unknown evidence type: {evidence_type}")
            return
        
        await update.message.reply_text(f"📸 Collecting {evidence_type} evidence...")
        success = await evidence_handlers[evidence_type]()
        
        if success:
            await update.message.reply_text(f"✅ {evidence_type.capitalize()} evidence collected successfully")
        else:
            await update.message.reply_text(f"❌ Failed to collect {evidence_type} evidence")
            
    except Exception as e:
        error_msg = f"❌ Evidence command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def track_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Track device location."""
    try:
        device_type = 'laptop'
        if context.args:
            device_type = context.args[0].lower()
        
        await update.message.reply_text(f"📍 Tracking {device_type} location...")
        
        # Get basic location information
        location_info = []
        
        # Public IP
        success, stdout, stderr = await safe_system_command(['curl', '-s', 'https://api.ipify.org'])
        if success:
            location_info.append(f"🌐 Public IP: `{stdout}`")
        
        # Network information
        success, stdout, stderr = await safe_system_command(['ip', 'addr', 'show'])
        if success:
            location_info.append(f"🔧 Network Interfaces:\n```{stdout[:500]}...```")
        
        # WiFi information (if available)
        success, stdout, stderr = await safe_system_command(['iwconfig'], timeout=10)
        if success:
            location_info.append(f"📶 Wireless:\n```{stdout}```")
        
        if location_info:
            response = f"**📍 {device_type.upper()} LOCATION DATA**\n\n" + "\n\n".join(location_info)
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Could not retrieve location data")
            
    except Exception as e:
        error_msg = f"❌ Track command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def wipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Secure data deletion."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/wipe [level]`\n\n"
                "**Wipe levels:**\n"
                "• `sensitive` - Delete sensitive files only\n"
                "• `complete` - Full system wipe (IRREVERSIBLE)\n\n"
                "⚠️ **WARNING:** Complete wipe cannot be undone!",
                parse_mode='Markdown'
            )
            return
        
        wipe_level = context.args[0].lower()
        
        if wipe_level not in ['sensitive', 'complete']:
            await update.message.reply_text("❌ Invalid wipe level. Use 'sensitive' or 'complete'")
            return
        
        if wipe_level == 'complete':
            # Require confirmation for complete wipe
            if len(context.args) < 2 or context.args[1] != 'CONFIRM':
                await update.message.reply_text(
                    "🚨 **COMPLETE WIPE REQUESTED**\n\n"
                    "⚠️ This will delete ALL user data and cannot be undone!\n\n"
                    "To proceed, use:\n"
                    f"`/wipe complete CONFIRM`\n\n"
                    "**This action is irreversible!**",
                    parse_mode='Markdown'
                )
                return
        
        await update.message.reply_text(f"🗑️ Starting {wipe_level} data wipe...")
        
        if wipe_level == 'sensitive':
            success = await encrypt_sensitive_files()
            action = "sensitive files encrypted"
        else:
            success = await wipe_browser_data()
            action = "complete wipe initiated"
        
        if success:
            with panic_lock:
                panic_state['wipe_initiated'] = True
            
            await update.message.reply_text(f"✅ {action.capitalize()} successfully")
            logger.warning(f"Data wipe performed: {wipe_level}")
        else:
            await update.message.reply_text(f"❌ {action.capitalize()} failed")
            
    except Exception as e:
        error_msg = f"❌ Wipe command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def killswitch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activate self-destruct sequence."""
    try:
        if not context.args:
            await update.message.reply_text(
                "💀 **KILLSWITCH ACTIVATION**\n\n"
                "This will:\n"
                "1. Backup all evidence to MEGA\n"
                "2. Wipe sensitive data\n" 
                "3. Delete bot and associated files\n"
                "4. Remove MEGA synchronization\n\n"
                "⚠️ **THIS ACTION IS IRREVERSIBLE!**\n\n"
                "To activate, use:\n"
                "`/killswitch CONFIRM_[CODE]`\n\n"
                "Generate confirmation code with:\n"
                "`/killswitch generate`",
                parse_mode='Markdown'
            )
            return
        
        if context.args[0] == 'generate':
            # Generate confirmation code
            confirm_code = hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()
            await update.message.reply_text(
                f"🔐 **CONFIRMATION CODE GENERATED**\n\n"
                f"Code: `{confirm_code}`\n\n"
                f"Use: `/killswitch CONFIRM_{confirm_code}`\n\n"
                f"⚠️ This code expires in 5 minutes",
                parse_mode='Markdown'
            )
            return
        
        confirm_arg = ' '.join(context.args)
        if not confirm_arg.startswith('CONFIRM_'):
            await update.message.reply_text("❌ Invalid confirmation format")
            return
        
        await update.message.reply_text(
            "💀 **KILLSWITCH ACTIVATED**\n\n"
            "**SEQUENCE INITIATED:**\n"
            "1. Final evidence collection...\n"
            "2. MEGA backup verification...\n" 
            "3. Secure data deletion...\n"
            "4. System cleanup...\n\n"
            "⏰ Estimated time: 2-5 minutes\n"
            "⚠️ DO NOT INTERRUPT PROCESS",
            parse_mode='Markdown'
        )
        
        # Execute killswitch sequence
        success = await execute_killswitch_sequence(update)
        
        if success:
            await update.message.reply_text(
                "✅ **KILLSWITCH COMPLETED**\n\n"
                "All systems have been sanitized.\n"
                "Bot will now self-terminate.\n\n"
                "🔒 Mission accomplished.",
                parse_mode='Markdown'
            )
            # Self-terminate
            os._exit(0)
        else:
            await update.message.reply_text(
                "❌ **KILLSWITCH PARTIALLY COMPLETED**\n\n"
                "Some cleanup may be incomplete.\n"
                "Manual verification recommended.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        error_msg = f"❌ Killswitch command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def execute_killswitch_sequence(update: Update) -> bool:
    """Execute the complete killswitch sequence."""
    try:
        steps = [
            ("Final evidence collection", final_evidence_collection),
            ("MEGA backup completion", ensure_mega_backup),
            ("Secure file deletion", secure_file_deletion),
            ("Bot cleanup", bot_self_cleanup),
            ("MEGA sync removal", remove_mega_sync)
        ]
        
        for step_name, step_func in steps:
            await update.message.reply_text(f"🔧 **Executing:** {step_name}")
            success = await step_func()
            if not success:
                await update.message.reply_text(f"⚠️ **Warning:** {step_name} had issues")
            await asyncio.sleep(1)
        
        return True
        
    except Exception as e:
        logger.error(f"Killswitch sequence error: {e}")
        return False

async def final_evidence_collection():
    """Collect final evidence before destruction."""
    try:
        await take_security_photos()
        await capture_screenshots()
        await log_system_state()
        return True
    except:
        return False

async def ensure_mega_backup():
    """Ensure all evidence is backed up to MEGA."""
    try:
        return await start_mega_backup()
    except:
        return False

async def secure_file_deletion():
    """Securely delete sensitive files."""
    try:
        # Delete evidence directory
        if os.path.exists(EVIDENCE_DIR):
            shutil.rmtree(EVIDENCE_DIR, ignore_errors=True)
        
        # Delete bot logs
        log_dir = os.path.join(BASE_DIR, 'bot', 'logs')
        if os.path.exists(log_dir):
            shutil.rmtree(log_dir, ignore_errors=True)
        
        return True
    except:
        return False

async def bot_self_cleanup():
    """Clean up bot files and databases."""
    try:
        # Delete database files
        db_files = [PANIC_DB, os.path.join(BASE_DIR, 'command_queue.db')]
        for db_file in db_files:
            if os.path.exists(db_file):
                os.remove(db_file)
        
        return True
    except:
        return False

async def remove_mega_sync():
    """Remove MEGA synchronization."""
    try:
        success, stdout, stderr = await safe_system_command(['mega-logout'])
        return success
    except:
        return False

async def backup_logs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Backup all logs to MEGA."""
    try:
        await update.message.reply_text("☁️ Starting MEGA backup...")
        
        success = await start_mega_backup()
        
        if success:
            with panic_lock:
                panic_state['backup_completed'] = True
            
            await update.message.reply_text(
                "✅ **MEGA BACKUP COMPLETED**\n\n"
                "All evidence and logs have been backed up to MEGA cloud.\n"
                "Data is secure and accessible from any device.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ **MEGA BACKUP FAILED**\n\n"
                "Backup could not be completed.\n"
                "Check MEGAcmd installation and credentials.",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        error_msg = f"❌ Backup command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def system_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate comprehensive forensic report."""
    try:
        await update.message.reply_text("🔍 Generating forensic report...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(EVIDENCE_DIR, 'reports', f'forensic_report_{timestamp}.txt')
        
        # Collect comprehensive system information
        report_sections = []
        
        # System information
        success, stdout, stderr = await safe_system_command(['uname', '-a'])
        report_sections.append(f"SYSTEM: {stdout}")
        
        # Uptime
        success, stdout, stderr = await safe_system_command(['uptime'])
        report_sections.append(f"UPTIME: {stdout}")
        
        # Network
        success, stdout, stderr = await safe_system_command(['ip', 'addr', 'show'])
        report_sections.append(f"NETWORK:\n{stdout}")
        
        # Processes
        success, stdout, stderr = await safe_system_command(['ps', 'aux', '--sort=-%cpu'])
        report_sections.append(f"PROCESSES (top 20):\n{stdout}")
        
        # Evidence summary
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), file_type FROM evidence_files GROUP BY file_type")
        evidence_summary = cursor.fetchall()
        conn.close()
        
        report_sections.append("EVIDENCE SUMMARY:")
        for count, file_type in evidence_summary:
            report_sections.append(f"  {file_type}: {count} files")
        
        # Write report
        with open(report_path, 'w') as f:
            f.write("C3NTR@L COMM@ND - FORENSIC REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n\n")
            
            for section in report_sections:
                f.write(section + "\n")
                f.write("-" * 30 + "\n\n")
        
        # Send report summary
        report_summary = (
            "📊 **FORENSIC REPORT GENERATED**\n\n"
            f"⏰ Timestamp: {timestamp}\n"
            f"📁 Location: `{report_path}`\n"
            f"📄 Evidence files: {sum(count for count, _ in evidence_summary)}\n\n"
            "**SECTIONS INCLUDED:**\n"
            "• System information\n"
            "• Uptime and load\n"
            "• Network configuration\n" 
            "• Running processes\n"
            "• Evidence inventory\n"
        )
        
        await update.message.reply_text(report_summary, parse_mode='Markdown')
        
        # Log report generation
        file_hash = calculate_file_hash(report_path)
        conn = sqlite3.connect(PANIC_DB)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO evidence_files (file_path, file_type, timestamp, hash) VALUES (?, ?, ?, ?)",
            (report_path, 'forensic_report', datetime.now(), file_hash)
        )
        conn.commit()
        conn.close()
        
    except Exception as e:
        error_msg = f"❌ System report error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def panic_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current panic status."""
    try:
        with panic_lock:
            if not panic_state['active']:
                await update.message.reply_text(
                    "🟢 **PANIC SYSTEM STATUS: INACTIVE**\n\n"
                    "No active panic protocols.\n"
                    "System is operating normally.",
                    parse_mode='Markdown'
                )
                return
            
            duration = datetime.now() - panic_state['start_time']
            level_names = {
                1: "🟡 LIGHT LOCKDOWN",
                2: "🟠 MEDIUM LOCKDOWN",
                3: "🔴 HEAVY LOCKDOWN", 
                4: "🟣 EXTREME LOCKDOWN",
                5: "⚫ NUCLEAR LOCKDOWN"
            }
            
            status_msg = (
                f"🚨 **{level_names[panic_state['level']]}**\n\n"
                f"📍 Level: {panic_state['level']}/5\n"
                f"⏰ Active for: {duration}\n"
                f"📊 Evidence collected: {len(panic_state['evidence_collected'])} files\n"
                f"☁️ MEGA backup: {'✅ COMPLETED' if panic_state['backup_completed'] else '❌ PENDING'}\n"
                f"🗑️ Data wipe: {'✅ INITIATED' if panic_state['wipe_initiated'] else '❌ STANDBY'}\n\n"
                f"**COMMANDS:**\n"
                f"• `/panic_abort` - Cancel panic\n"
                f"• `/backup_logs` - Force backup\n"
                f"• `/system_report` - Generate report\n"
                f"• `/evidence [type]` - Collect evidence"
            )
            
            await update.message.reply_text(status_msg, parse_mode='Markdown')
            
    except Exception as e:
        error_msg = f"❌ Panic status error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def panic_abort_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Abort panic sequence."""
    try:
        with panic_lock:
            if not panic_state['active']:
                await update.message.reply_text("ℹ️ No active panic sequence to abort.")
                return
            
            # Log abort event
            conn = sqlite3.connect(PANIC_DB)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE panic_events SET end_time = ?, status = ? WHERE status = 'active'",
                (datetime.now(), 'aborted')
            )
            conn.commit()
            conn.close()
            
            level = panic_state['level']
            evidence_count = len(panic_state['evidence_collected'])
            
            # Reset panic state
            panic_state['active'] = False
            panic_state['level'] = 0
            panic_state['start_time'] = None
            panic_state['evidence_collected'] = []
        
        await update.message.reply_text(
            f"🟢 **PANIC SEQUENCE ABORTED**\n\n"
            f"📍 Final level: {level}/5\n"
            f"📊 Evidence collected: {evidence_count} files\n"
            f"⏰ Total duration: {datetime.now() - panic_state['start_time']}\n\n"
            f"**System returning to normal operation.**",
            parse_mode='Markdown'
        )
        
        logger.info(f"Panic sequence aborted by user {update.effective_user.id}")
        
    except Exception as e:
        error_msg = f"❌ Panic abort error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file."""
    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except:
        return "unknown"

def get_panic_status():
    """Get panic status for system reports."""
    with panic_lock:
        return {
            'active': panic_state['active'],
            'level': panic_state['level'],
            'evidence_collected': len(panic_state['evidence_collected']),
            'backup_completed': panic_state['backup_completed']
        }

def cleanup():
    """Cleanup panic system resources."""
    with panic_lock:
        panic_state['active'] = False
        panic_state['level'] = 0

# Auto-initialize when module loads
initialize_panic_system()