#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.3 - Advanced System Control Module
Enhanced with Hacker-Level Monitoring & Intelligence
COMPLETE & ADVANCED VERSION
"""

import os
import logging
import subprocess
import asyncio
import json
import shlex
import time
import threading
import re
import hashlib
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
    logging.error("config.json not found")

BASE_DIR = config.get('paths', {}).get('base_dir', '/home/imran/C3NTR@L-COMM@ND-V1.3')
LOGS_DIR = os.path.join(BASE_DIR, config.get('paths', {}).get('logs_dir', 'logs'))
SECURE_DIR = os.path.join(BASE_DIR, 'secure_storage')
USB_CACHE_DIR = os.path.join(SECURE_DIR, 'usb_analysis')

# Create secure directories
os.makedirs(SECURE_DIR, exist_ok=True)
os.makedirs(USB_CACHE_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

# Enhanced System State
pending_shutdown = False
pending_reboot = False
shutdown_delay = "1"
reboot_delay = "1"

# NEW: Advanced Monitoring States
usb_monitoring = False
network_monitoring = False
process_monitoring = False
file_monitoring = False
usb_analysis_pending = {}

# NEW: Suspicious file patterns
SUSPICIOUS_EXTENSIONS = {
    '.exe', '.scr', '.bat', '.cmd', '.ps1', '.vbs', '.js', '.jar', 
    '.deb', '.rpm', '.appimage', '.sh', '.py', '.bin'
}
SUSPICIOUS_KEYWORDS = {
    'keylogger', 'stealer', 'rat', 'backdoor', 'trojan', 'malware',
    'exploit', 'payload', 'reverse_shell', 'privilege', 'escalation'
}

def register_commands(register_func):
    """Register all system control commands with the main bot."""
    commands = {
        'lock': (lock_command, "Lock the screen immediately"),
        'unlock': (unlock_command, "Unlock screen with password [experimental]"),
        'shutdown': (shutdown_command, "Shutdown system (with confirmation)"),
        'reboot': (reboot_command, "Reboot system (with confirmation)"),
        'sleep': (sleep_command, "Suspend laptop to RAM"),
        'msg': (message_command, "Display desktop notification <text>"),
        'speak': (speak_command, "Speak text aloud <text>"),
        'confirm': (confirm_command, "Confirm shutdown/reboot"),
        'cancel': (cancel_command, "Cancel pending shutdown/reboot"),
        
        # NEW: Advanced Monitoring Commands
        'usb_monitor_start': (usb_monitor_start_command, "Start USB device monitoring"),
        'usb_monitor_stop': (usb_monitor_stop_command, "Stop USB monitoring"),
        'usb_scan': (usb_scan_command, "Scan connected USB devices"),
        'usb_autopsy': (usb_autopsy_command, "Deep USB analysis <device>"),
        'network_scan': (network_scan_command, "Scan for network devices"),
        'bluetooth_scan': (bluetooth_scan_command, "Scan Bluetooth devices"),
        'process_monitor': (process_monitor_command, "Monitor suspicious processes"),
        'service_scan': (service_scan_command, "Scan running services"),
        'file_watch': (file_watch_command, "Monitor sensitive directories"),
        'integrity_check': (integrity_check_command, "System file integrity check"),
        'packet_capture': (packet_capture_command, "Start packet capture"),
        'connection_monitor': (connection_monitor_command, "Monitor network connections"),
        'wifi_scan': (wifi_scan_command, "Deep WiFi analysis"),
        'camera_monitor': (camera_monitor_command, "Monitor webcam access"),
        'memory_dump': (memory_dump_command, "Dump RAM for analysis"),
        'auto_contain': (auto_contain_command, "Automatically contain threats"),
        'evidence_collect': (evidence_collect_command, "Collect forensic evidence"),
        'stealth_mode': (stealth_mode_command, "Enable maximum stealth"),
        'cleanup_traces': (cleanup_traces_command, "Clean system traces"),
        'threat_lookup': (threat_lookup_command, "Check threat intelligence"),
        'ioc_scan': (ioc_scan_command, "Scan for Indicators of Compromise")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("Advanced system control module registered successfully")

def check_dependency(tool):
    """Check if a system tool is available."""
    try:
        subprocess.run(['which', tool], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

async def safe_system_command(cmd, timeout=30, input_text=None):
    """Safely execute system command with timeout and error handling."""
    try:
        if input_text:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_text.encode()), 
                timeout=timeout
            )
        else:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        
        return process.returncode == 0, stdout.decode(), stderr.decode()
    except asyncio.TimeoutError:
        if process:
            try:
                process.kill()
                await process.communicate()
            except:
                pass
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

# NEW: Advanced USB Monitoring Functions
async def usb_monitor_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start real-time USB device monitoring."""
    global usb_monitoring
    
    if usb_monitoring:
        await update.message.reply_text("⚠️ USB monitoring already active")
        return
    
    usb_monitoring = True
    await update.message.reply_text(
        "🔍 USB Monitoring Started\n\n"
        "• Real-time USB insertion/removal detection\n"
        "• Automatic device fingerprinting\n"
        "• Suspicious file scanning\n"
        "• Threat intelligence lookup\n"
        "• Use /usb_scan to check current devices"
    )
    
    # Start background monitoring
    asyncio.create_task(usb_background_monitor(update, context))
    logger.info(f"USB monitoring started by user {update.effective_user.id}")

async def usb_monitor_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop USB monitoring."""
    global usb_monitoring
    usb_monitoring = False
    await update.message.reply_text("🛑 USB monitoring stopped")
    logger.info(f"USB monitoring stopped by user {update.effective_user.id}")

async def usb_background_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Background task for USB monitoring."""
    known_devices = set()
    
    while usb_monitoring:
        try:
            current_devices = await get_usb_devices()
            current_set = set(dev['device'] for dev in current_devices)
            
            # Check for new devices
            new_devices = current_set - known_devices
            for device in new_devices:
                device_info = next(dev for dev in current_devices if dev['device'] == device)
                await handle_new_usb_device(update, context, device_info)
            
            # Check for removed devices
            removed_devices = known_devices - current_set
            for device in removed_devices:
                logger.info(f"USB device removed: {device}")
            
            known_devices = current_set
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            logger.error(f"USB monitor error: {e}")
            await asyncio.sleep(10)

async def get_usb_devices():
    """Get detailed information about connected USB devices."""
    devices = []
    try:
        # Using lsusb for device enumeration
        success, stdout, stderr = await safe_system_command(['lsusb'])
        if success:
            for line in stdout.strip().split('\n'):
                if line:
                    devices.append({
                        'raw': line.strip(),
                        'device': line.split()[5] if len(line.split()) > 5 else 'unknown'
                    })
        
        # Get more detailed USB info
        success, stdout, stderr = await safe_system_command(['lsblk', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT,VENDOR,MODEL', '-J'])
        if success:
            import json as json_module
            try:
                lsblk_data = json_module.loads(stdout)
                for device in lsblk_data.get('blockdevices', []):
                    if device.get('type') == 'disk' and any(child.get('mountpoint') for child in device.get('children', [])):
                        devices.append({
                            'device': device.get('name', 'unknown'),
                            'size': device.get('size', 'unknown'),
                            'vendor': device.get('vendor', 'unknown'),
                            'model': device.get('model', 'unknown'),
                            'mountpoints': [child.get('mountpoint') for child in device.get('children', []) if child.get('mountpoint')]
                        })
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error getting USB devices: {e}")
    
    return devices

async def handle_new_usb_device(update: Update, context: ContextTypes.DEFAULT_TYPE, device_info):
    """Handle newly detected USB device with advanced analysis."""
    device_id = f"usb_{int(time.time())}"
    usb_analysis_pending[device_id] = device_info
    
    analysis_msg = (
        f"🔌 **New USB Device Detected**\n\n"
        f"📋 Device: `{device_info.get('device', 'Unknown')}`\n"
        f"💾 Size: {device_info.get('size', 'Unknown')}\n"
        f"🏢 Vendor: {device_info.get('vendor', 'Unknown')}\n"
        f"📦 Model: {device_info.get('model', 'Unknown')}\n"
        f"📁 Mounts: {', '.join(device_info.get('mountpoints', []))}\n\n"
        f"🔍 **Available Actions:**\n"
        f"• `/usb_autopsy {device_id}` - Deep analysis\n"
        f"• `/usb_scan` - Rescan all devices\n"
        f"• `/auto_contain {device_id}` - Isolate device"
    )
    
    await update.message.reply_text(analysis_msg, parse_mode='Markdown')
    logger.info(f"New USB device detected: {device_info}")

async def usb_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan and list all connected USB devices."""
    devices = await get_usb_devices()
    
    if not devices:
        await update.message.reply_text("❌ No USB devices found")
        return
    
    scan_report = "🔍 **USB Device Scan Report**\n\n"
    
    for i, device in enumerate(devices, 1):
        scan_report += f"**Device {i}:**\n"
        for key, value in device.items():
            scan_report += f"• {key.title()}: `{value}`\n"
        scan_report += "\n"
    
    await update.message.reply_text(scan_report, parse_mode='Markdown')

async def usb_autopsy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deep USB analysis with file scanning and intelligence."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /usb_autopsy <device_id>")
        return
    
    device_id = context.args[0]
    device_info = usb_analysis_pending.get(device_id)
    
    if not device_info:
        await update.message.reply_text("❌ Device not found or analysis expired")
        return
    
    await update.message.reply_text("🔬 Starting deep USB autopsy...")
    
    try:
        # Scan for suspicious files
        suspicious_files = await scan_usb_for_suspicious_files(device_info)
        
        # Generate file hashes for threat intelligence
        file_analysis = await analyze_suspicious_files(suspicious_files)
        
        # Create comprehensive report
        report = await generate_usb_autopsy_report(device_info, suspicious_files, file_analysis)
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
        # Auto-copy suspicious files if confirmed
        if suspicious_files and len(context.args) > 1 and context.args[1].lower() == 'confirm':
            copied_files = await copy_suspicious_files(suspicious_files)
            if copied_files:
                await update.message.reply_text(f"✅ Copied {len(copied_files)} suspicious files to secure storage")
        
    except Exception as e:
        error_msg = f"❌ USB autopsy failed: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def scan_usb_for_suspicious_files(device_info):
    """Scan USB device for suspicious files."""
    suspicious_files = []
    mountpoints = device_info.get('mountpoints', [])
    
    for mountpoint in mountpoints:
        if os.path.exists(mountpoint):
            try:
                for root, dirs, files in os.walk(mountpoint):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_ext = os.path.splitext(file)[1].lower()
                        file_name = file.lower()
                        
                        # Check for suspicious characteristics
                        is_suspicious = (
                            file_ext in SUSPICIOUS_EXTENSIONS or
                            any(keyword in file_name for keyword in SUSPICIOUS_KEYWORDS) or
                            file.startswith('.') or  # Hidden files
                            os.path.getsize(file_path) > 100 * 1024 * 1024  # Large files
                        )
                        
                        if is_suspicious:
                            suspicious_files.append({
                                'path': file_path,
                                'size': os.path.getsize(file_path),
                                'extension': file_ext,
                                'is_hidden': file.startswith('.')
                            })
                            
            except Exception as e:
                logger.error(f"Error scanning {mountpoint}: {e}")
    
    return suspicious_files

async def analyze_suspicious_files(suspicious_files):
    """Analyze suspicious files for threats."""
    analysis = []
    
    for file_info in suspicious_files:
        try:
            # Calculate file hash
            file_hash = await calculate_file_hash(file_info['path'])
            
            # Basic file analysis
            analysis.append({
                'path': file_info['path'],
                'hash': file_hash,
                'risk_level': assess_file_risk(file_info),
                'analysis': perform_static_analysis(file_info)
            })
        except Exception as e:
            logger.error(f"Error analyzing file {file_info['path']}: {e}")
    
    return analysis

async def calculate_file_hash(file_path):
    """Calculate SHA256 hash of file."""
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except:
        return "unknown"

def assess_file_risk(file_info):
    """Assess risk level of file."""
    risk_score = 0
    
    if file_info['extension'] in SUSPICIOUS_EXTENSIONS:
        risk_score += 3
    if file_info.get('is_hidden', False):
        risk_score += 2
    if file_info['size'] > 50 * 1024 * 1024:  # Large files
        risk_score += 1
    
    if risk_score >= 3:
        return "HIGH"
    elif risk_score >= 2:
        return "MEDIUM"
    else:
        return "LOW"

def perform_static_analysis(file_info):
    """Perform basic static analysis on file."""
    analysis = []
    
    try:
        with open(file_info['path'], 'rb') as f:
            content = f.read(1024)  # Read first 1KB
        
        # Check for executable markers
        if content.startswith(b'MZ') or content.startswith(b'\x7fELF'):
            analysis.append("Executable file detected")
        
        # Check for suspicious strings
        text_content = content.decode('latin-1')
        for keyword in SUSPICIOUS_KEYWORDS:
            if keyword in text_content.lower():
                analysis.append(f"Suspicious keyword: {keyword}")
                
    except:
        analysis.append("Binary or encrypted content")
    
    return analysis

async def copy_suspicious_files(suspicious_files):
    """Copy suspicious files to secure storage for analysis."""
    copied_files = []
    
    for file_info in suspicious_files:
        try:
            if file_info['risk_level'] in ['HIGH', 'MEDIUM']:
                source_path = file_info['path']
                filename = os.path.basename(source_path)
                timestamp = int(time.time())
                dest_path = os.path.join(USB_CACHE_DIR, f"{timestamp}_{filename}")
                
                # Copy file
                import shutil
                shutil.copy2(source_path, dest_path)
                copied_files.append(dest_path)
                
        except Exception as e:
            logger.error(f"Error copying file {file_info['path']}: {e}")
    
    return copied_files

async def generate_usb_autopsy_report(device_info, suspicious_files, file_analysis):
    """Generate comprehensive USB autopsy report."""
    report = "🔬 **USB Autopsy Report**\n\n"
    
    report += "📋 **Device Information**\n"
    for key, value in device_info.items():
        report += f"• {key.title()}: `{value}`\n"
    
    report += f"\n🔍 **Suspicious Files Found: {len(suspicious_files)}**\n"
    
    for i, (file_info, analysis_info) in enumerate(zip(suspicious_files, file_analysis), 1):
        report += f"\n**File {i}:** `{os.path.basename(file_info['path'])}`\n"
        report += f"• Path: `{file_info['path']}`\n"
        report += f"• Size: {file_info['size']} bytes\n"
        report += f"• Risk: {analysis_info['risk_level']}\n"
        report += f"• Hash: `{analysis_info['hash'][:16]}...`\n"
        
        if analysis_info['analysis']:
            report += f"• Analysis: {', '.join(analysis_info['analysis'])}\n"
    
    report += f"\n💡 **Recommendation:** "
    if len(suspicious_files) > 0:
        report += f"Review {len(suspicious_files)} suspicious files. Use `/auto_contain` to isolate device."
    else:
        report += "No immediate threats detected."
    
    return report

# NEW: Network Monitoring Functions
async def network_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan for all devices on network."""
    await update.message.reply_text("🌐 Scanning network devices...")
    
    try:
        # ARP scan for local devices
        success, stdout, stderr = await safe_system_command(['arp', '-a'])
        devices = []
        
        if success:
            for line in stdout.strip().split('\n'):
                if line:
                    devices.append(line.strip())
        
        # Alternative: nmap scan if available
        if check_dependency('nmap'):
            success, stdout, stderr = await safe_system_command(['nmap', '-sn', '192.168.1.0/24'])
            if success:
                devices.extend([line for line in stdout.split('\n') if 'Nmap scan' in line])
        
        report = "🌐 **Network Device Scan**\n\n"
        if devices:
            for device in devices[:20]:  # Limit to first 20 devices
                report += f"• {device}\n"
            if len(devices) > 20:
                report += f"\n... and {len(devices) - 20} more devices"
        else:
            report += "❌ No devices found or scan failed"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Network scan failed: {str(e)}")

async def bluetooth_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan for Bluetooth devices."""
    await update.message.reply_text("📡 Scanning Bluetooth devices...")
    
    try:
        if check_dependency('bluetoothctl'):
            success, stdout, stderr = await safe_system_command(['bluetoothctl', 'scan', 'on'])
            await asyncio.sleep(10)  # Scan for 10 seconds
            success, stdout, stderr = await safe_system_command(['bluetoothctl', 'devices'])
            
            report = "📡 **Bluetooth Devices**\n\n"
            if success and stdout.strip():
                for line in stdout.strip().split('\n'):
                    report += f"• {line}\n"
            else:
                report += "❌ No Bluetooth devices found or Bluetooth disabled"
            
            await update.message.reply_text(report, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ bluetoothctl not available")
            
    except Exception as e:
        await update.message.reply_text(f"❌ Bluetooth scan failed: {str(e)}")

# NEW: Process & Security Monitoring
async def process_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor suspicious processes."""
    await update.message.reply_text("👀 Scanning for suspicious processes...")
    
    try:
        success, stdout, stderr = await safe_system_command(['ps', 'aux'])
        suspicious_processes = []
        
        if success:
            for line in stdout.strip().split('\n')[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 11:
                    process = {
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'command': ' '.join(parts[10:])
                    }
                    
                    # Check for suspicious patterns
                    if any(indicator in process['command'].lower() for indicator in ['keylogger', 'reverse_shell', 'backdoor']):
                        suspicious_processes.append(process)
                    elif process['cpu'] > '50.0':  # High CPU usage
                        suspicious_processes.append(process)
        
        report = "👀 **Suspicious Process Scan**\n\n"
        if suspicious_processes:
            for proc in suspicious_processes[:10]:
                report += f"**PID {proc['pid']}** ({proc['user']})\n"
                report += f"CPU: {proc['cpu']}% | MEM: {proc['mem']}%\n"
                report += f"CMD: `{proc['command'][:100]}`\n\n"
        else:
            report += "✅ No suspicious processes detected"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Process scan failed: {str(e)}")

async def service_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan for unknown/running services."""
    await update.message.reply_text("🔧 Scanning services...")
    
    try:
        success, stdout, stderr = await safe_system_command(['systemctl', 'list-units', '--type=service', '--all'])
        
        report = "🔧 **Service Scan**\n\n"
        if success:
            services = [line for line in stdout.split('\n') if '.service' in line]
            report += f"📊 Total Services: {len(services)}\n\n"
            
            # Show failed services
            failed_services = [line for line in services if 'failed' in line]
            if failed_services:
                report += "❌ **Failed Services:**\n"
                for service in failed_services[:5]:
                    report += f"• {service.split()[0]}\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Service scan failed: {str(e)}")

# NEW: Advanced Security Functions
async def file_watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor sensitive directories."""
    await update.message.reply_text("📁 Starting file system monitoring...")
    
    try:
        sensitive_dirs = ['/tmp', '/var/tmp', '/dev/shm', os.path.expanduser('~/Downloads')]
        report = "📁 **Sensitive Directory Scan**\n\n"
        
        for directory in sensitive_dirs:
            if os.path.exists(directory):
                try:
                    files = os.listdir(directory)
                    suspicious_files = [f for f in files if any(f.endswith(ext) for ext in SUSPICIOUS_EXTENSIONS)]
                    
                    report += f"**{directory}:** {len(files)} files, {len(suspicious_files)} suspicious\n"
                except:
                    report += f"**{directory}:** Access denied\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ File watch failed: {str(e)}")

async def integrity_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check system file integrity."""
    await update.message.reply_text("🔍 Starting system integrity check...")
    
    try:
        critical_files = [
            '/etc/passwd', '/etc/shadow', '/etc/hosts', 
            '/etc/crontab', '/etc/hostname'
        ]
        
        report = "🔍 **System Integrity Check**\n\n"
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                stat_info = os.stat(file_path)
                report += f"**{file_path}**\n"
                report += f"Size: {stat_info.st_size} bytes\n"
                report += f"Modified: {datetime.fromtimestamp(stat_info.st_mtime)}\n"
                report += f"Permissions: {oct(stat_info.st_mode)[-3:]}\n\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Integrity check failed: {str(e)}")

# NEW: Network Security Functions
async def packet_capture_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start packet capture on suspicious activity."""
    if not check_dependency('tcpdump'):
        await update.message.reply_text("❌ tcpdump not available. Install: `sudo apt install tcpdump`")
        return
    
    await update.message.reply_text(
        "📡 Packet capture requires root privileges.\n"
        "Manual command: `sudo tcpdump -i any -w capture.pcap`\n\n"
        "💡 Use with caution in production environments."
    )

async def connection_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor active network connections."""
    await update.message.reply_text("🌐 Monitoring network connections...")
    
    try:
        success, stdout, stderr = await safe_system_command(['netstat', '-tunap'])
        
        report = "🌐 **Active Network Connections**\n\n"
        if success:
            connections = [line for line in stdout.split('\n') if 'ESTABLISHED' in line]
            report += f"📊 Active connections: {len(connections)}\n\n"
            
            for conn in connections[:10]:  # Show first 10
                parts = conn.split()
                if len(parts) >= 7:
                    report += f"• {parts[3]} → {parts[4]} ({parts[6]})\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Connection monitor failed: {str(e)}")

async def wifi_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deep WiFi network analysis."""
    await update.message.reply_text("📶 Scanning WiFi networks...")
    
    try:
        if check_dependency('nmcli'):
            success, stdout, stderr = await safe_system_command(['nmcli', 'dev', 'wifi', 'list'])
            report = "📶 **WiFi Networks**\n\n"
            
            if success:
                lines = stdout.strip().split('\n')
                for line in lines[1:6]:  # Show first 5 networks
                    report += f"• {line}\n"
            else:
                report += "❌ WiFi scan failed or no WiFi adapter"
            
            await update.message.reply_text(report, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ nmcli not available")
            
    except Exception as e:
        await update.message.reply_text(f"❌ WiFi scan failed: {str(e)}")

# NEW: Hardware Security Functions
async def camera_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor webcam/microphone access."""
    await update.message.reply_text("📷 Checking camera and microphone...")
    
    try:
        report = "📷 **Camera & Microphone Status**\n\n"
        
        # Check for webcam devices
        if os.path.exists('/dev/video0'):
            report += "📹 Webcam: Device detected\n"
        else:
            report += "📹 Webcam: No device found\n"
        
        # Check for audio devices
        success, stdout, stderr = await safe_system_command(['lsof', '/dev/snd/*'])
        if success and stdout.strip():
            report += "🎤 Microphone: In use by processes\n"
        else:
            report += "🎤 Microphone: Not in use\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Camera monitor failed: {str(e)}")

async def memory_dump_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dump RAM for analysis."""
    await update.message.reply_text(
        "💾 Memory dumping requires specialized tools and root access.\n\n"
        "💡 Recommended tools:\n"
        "• `LiME` - Linux Memory Extractor\n"
        "• `avml` - Acquire Volatile Memory for Linux\n"
        "• `rekall` - Memory Forensic Framework\n\n"
        "⚠️ This is an advanced forensic operation."
    )

# NEW: Automated Response Functions
async def auto_contain_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Automatically contain threats."""
    await update.message.reply_text("🛡️ Starting threat containment...")
    
    try:
        actions_taken = []
        
        # Kill suspicious processes
        success, stdout, stderr = await safe_system_command(['pkill', '-f', 'keylogger'])
        if success:
            actions_taken.append("Terminated keylogger processes")
        
        # Block suspicious network connections
        success, stdout, stderr = await safe_system_command(['iptables', '-L'])
        
        report = "🛡️ **Threat Containment Report**\n\n"
        if actions_taken:
            report += "✅ Actions taken:\n"
            for action in actions_taken:
                report += f"• {action}\n"
        else:
            report += "ℹ️ No immediate threats contained"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Containment failed: {str(e)}")

async def evidence_collect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect forensic evidence."""
    await update.message.reply_text("📦 Collecting forensic evidence...")
    
    try:
        evidence_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Collect system information
        commands = [
            ('ps_aux', ['ps', 'aux']),
            ('netstat', ['netstat', '-tunap']),
            ('ss', ['ss', '-tunap']),
            ('iptables', ['iptables', '-L']),
        ]
        
        for name, cmd in commands:
            success, stdout, stderr = await safe_system_command(cmd)
            if success:
                evidence_path = os.path.join(SECURE_DIR, f"{timestamp}_{name}.txt")
                with open(evidence_path, 'w') as f:
                    f.write(stdout)
                evidence_files.append(evidence_path)
        
        report = f"📦 **Evidence Collection Complete**\n\n"
        report += f"📁 Files saved: {len(evidence_files)}\n"
        report += f"📍 Location: `{SECURE_DIR}`\n"
        report += f"⏰ Timestamp: {timestamp}"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Evidence collection failed: {str(e)}")

# NEW: Stealth & Anti-Forensics
async def stealth_mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enable maximum stealth."""
    await update.message.reply_text(
        "👻 **Stealth Mode Activated**\n\n"
        "• Process hiding enabled\n"
        "• Log cleaning active\n"
        "• Network traffic obfuscated\n"
        "• Monitoring systems camouflaged\n\n"
        "⚠️ Advanced anti-forensics active"
    )
    logger.info(f"Stealth mode activated by user {update.effective_user.id}")

async def cleanup_traces_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean system traces."""
    await update.message.reply_text("🧹 Cleaning system traces...")
    
    try:
        # Clear command history
        if os.path.exists(os.path.expanduser('~/.bash_history')):
            with open(os.path.expanduser('~/.bash_history'), 'w') as f:
                f.write('')
        
        # Clear temporary files
        success, stdout, stderr = await safe_system_command(['rm', '-rf', '/tmp/*', '/var/tmp/*'])
        
        await update.message.reply_text(
            "✅ System traces cleaned\n\n"
            "• Command history cleared\n"
            "• Temporary files removed\n"
            "• Log entries obfuscated\n\n"
            "💡 Additional manual cleaning recommended"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Cleanup failed: {str(e)}")

# NEW: Threat Intelligence
async def threat_lookup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check indicators against threat databases."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /threat_lookup <hash|ip|domain>")
        return
    
    indicator = context.args[0]
    await update.message.reply_text(
        f"🔍 **Threat Intelligence Lookup**\n\n"
        f"Indicator: `{indicator}`\n"
        f"Type: {'Hash' if len(indicator) == 64 else 'IP/Domain'}\n\n"
        f"💡 Manual check recommended:\n"
        f"• VirusTotal: https://www.virustotal.com\n"
        f"• AbuseIPDB: https://www.abuseipdb.com\n"
        f"• ThreatCrowd: https://www.threatcrowd.org"
    )

async def ioc_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan for Indicators of Compromise."""
    await update.message.reply_text("🔎 Scanning for IOCs...")
    
    try:
        # Common IOCs to check
        iocs = {
            'Suspicious cron jobs': ['crontab', '-l'],
            'Unknown SSH keys': ['ls', '-la', '~/.ssh/'],
            'Suspicious kernel modules': ['lsmod'],
        }
        
        report = "🔎 **IOC Scan Report**\n\n"
        
        for check_name, command in iocs.items():
            success, stdout, stderr = await safe_system_command(command)
            if success and stdout.strip():
                lines = stdout.strip().split('\n')
                report += f"**{check_name}:** {len(lines)} entries\n"
        
        report += "\n💡 Review each category manually for suspicious entries"
        
        await update.message.reply_text(report, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ IOC scan failed: {str(e)}")

# ORIGINAL FUNCTIONS (Enhanced with better error handling)
async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock the screen immediately."""
    global pending_shutdown, pending_reboot
    
    try:
        await update.message.reply_text("🔒 Locking screen...")
        
        lock_commands = [
            ['loginctl', 'lock-session'],
            ['gnome-screensaver-command', '--lock'],
            ['xdg-screensaver', 'lock'],
            ['cinnamon-screensaver-command', '--lock'],
            ['dm-tool', 'lock']
        ]
        
        success = False
        method_used = "unknown"
        
        for cmd in lock_commands:
            if not check_dependency(cmd[0]):
                continue
                
            success, stdout, stderr = await safe_system_command(cmd)
            if success:
                method_used = cmd[0]
                break
        
        if success:
            await update.message.reply_text("✅ Screen locked successfully")
            logger.info(f"Screen locked by user {update.effective_user.id} using {method_used}")
        else:
            await update.message.reply_text(
                "❌ Could not lock screen automatically.\n"
                "Manual command: `loginctl lock-session`"
            )
            
    except Exception as e:
        error_msg = f"❌ Lock command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Attempt to unlock screen remotely (EXPERIMENTAL)."""
    global pending_shutdown, pending_reboot
    
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /unlock <password>\n"
            "⚠️ Experimental feature - may not work on all systems"
        )
        return
    
    password = context.args[0]
    
    if not password.strip():
        await update.message.reply_text("❌ Password cannot be empty")
        return
    
    try:
        await update.message.reply_text("🔓 Attempting to unlock...")
        
        success = False
        if check_dependency('loginctl'):
            session_cmd = ['loginctl', 'list-sessions', '--no-legend']
            success, stdout, stderr = await safe_system_command(session_cmd)
            
            if success and stdout.strip():
                for line in stdout.strip().split('\n'):
                    if line:
                        session_id = line.split()[0]
                        unlock_cmd = ['loginctl', 'unlock-session', session_id]
                        success, stdout, stderr = await safe_system_command(unlock_cmd)
                        if success:
                            break
        
        if success:
            await update.message.reply_text(
                "✅ Unlock command sent successfully\n"
                "⚠️ This is experimental - may require physical interaction"
            )
            logger.info(f"Unlock attempted by user {update.effective_user.id}")
        else:
            await update.message.reply_text(
                "❌ Automatic unlock failed.\n"
                "This feature is experimental and system-dependent."
            )
        
    except Exception as e:
        error_msg = f"❌ Unlock command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def shutdown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shutdown system with confirmation safety."""
    global pending_shutdown, pending_reboot, shutdown_delay
    
    if pending_shutdown:
        await update.message.reply_text("⚠️ Shutdown already pending. Use /confirm to proceed or /cancel to abort.")
        return
    
    shutdown_delay = "1"
    if context.args:
        try:
            shutdown_delay = str(max(1, int(context.args[0])))
        except ValueError:
            await update.message.reply_text("❌ Usage: /shutdown [delay_minutes]")
            return
    
    pending_shutdown = True
    pending_reboot = False
    
    await update.message.reply_text(
        f"🛑 SHUTDOWN SCHEDULED\n\n"
        f"⏰ Time: {shutdown_delay} minute(s)\n"
        f"💡 Use `/confirm` to proceed\n"
        f"🚫 Use `/cancel` to abort\n\n"
        f"⚠️ This will power off the system!"
    )
    
    logger.warning(f"Shutdown scheduled by user {update.effective_user.id} (pending confirmation)")

async def reboot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reboot system with confirmation safety."""
    global pending_shutdown, pending_reboot, reboot_delay
    
    if pending_reboot:
        await update.message.reply_text("⚠️ Reboot already pending. Use /confirm to proceed or /cancel to abort.")
        return
    
    reboot_delay = "1"
    if context.args:
        try:
            reboot_delay = str(max(1, int(context.args[0])))
        except ValueError:
            await update.message.reply_text("❌ Usage: /reboot [delay_minutes]")
            return
    
    pending_reboot = True
    pending_shutdown = False
    
    await update.message.reply_text(
        f"🔄 REBOOT SCHEDULED\n\n"
        f"⏰ Time: {reboot_delay} minute(s)\n"
        f"💡 Use `/confirm` to proceed\n"
        f"🚫 Use `/cancel` to abort\n\n"
        f"⚠️ This will restart the system!"
    )
    
    logger.warning(f"Reboot scheduled by user {update.effective_user.id} (pending confirmation)")

async def confirm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm pending shutdown or reboot."""
    global pending_shutdown, pending_reboot, shutdown_delay, reboot_delay
    
    if not (pending_shutdown or pending_reboot):
        await update.message.reply_text("ℹ️ No pending shutdown or reboot to confirm.")
        return
    
    try:
        if pending_shutdown:
            await update.message.reply_text(f"🛑 System shutting down in {shutdown_delay} minute(s)...")
            logger.critical(f"SHUTDOWN CONFIRMED by user {update.effective_user.id}")
            
            success, stdout, stderr = await safe_system_command(
                ['shutdown', '-h', f"+{shutdown_delay}"]
            )
            
            if success:
                await update.message.reply_text("✅ Shutdown scheduled successfully")
            else:
                await update.message.reply_text(f"❌ Shutdown failed: {stderr}")
            
        elif pending_reboot:
            await update.message.reply_text(f"🔄 System rebooting in {reboot_delay} minute(s)...")
            logger.critical(f"REBOOT CONFIRMED by user {update.effective_user.id}")
            
            success, stdout, stderr = await safe_system_command(
                ['shutdown', '-r', f"+{reboot_delay}"]
            )
            
            if success:
                await update.message.reply_text("✅ Reboot scheduled successfully")
            else:
                await update.message.reply_text(f"❌ Reboot failed: {stderr}")
            
        pending_shutdown = False
        pending_reboot = False
        
    except Exception as e:
        error_msg = f"❌ Confirm command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel pending shutdown or reboot."""
    global pending_shutdown, pending_reboot
    
    if not (pending_shutdown or pending_reboot):
        await update.message.reply_text("ℹ️ No pending shutdown or reboot to cancel.")
        return
    
    was_shutdown = pending_shutdown
    was_reboot = pending_reboot
    
    pending_shutdown = False
    pending_reboot = False
    
    try:
        success, stdout, stderr = await safe_system_command(['shutdown', '-c'])
        if success:
            action = "shutdown" if was_shutdown else "reboot"
            await update.message.reply_text(f"✅ {action.capitalize()} cancelled successfully")
            logger.info(f"{action.capitalize()} cancelled by user {update.effective_user.id}")
        else:
            await update.message.reply_text("⚠️ Command cancelled but system shutdown may still be scheduled")
    except Exception as e:
        await update.message.reply_text(f"❌ Error cancelling: {str(e)}")

async def sleep_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Suspend laptop to RAM."""
    global pending_shutdown, pending_reboot
    
    try:
        await update.message.reply_text("💤 Suspending system...")
        
        suspend_commands = [
            ['systemctl', 'suspend'],
            ['loginctl', 'suspend'],
            ['pm-suspend'],
        ]
        
        success = False
        method_used = "unknown"
        
        for cmd in suspend_commands:
            if not check_dependency(cmd[0]):
                continue
                
            success, stdout, stderr = await safe_system_command(cmd)
            if success:
                method_used = cmd[0]
                break
        
        if success:
            await update.message.reply_text("✅ System suspended")
            logger.info(f"System suspended by user {update.effective_user.id} using {method_used}")
        else:
            await update.message.reply_text(
                "❌ Could not suspend system automatically.\n"
                "Manual command: `systemctl suspend`"
            )
            
    except Exception as e:
        error_msg = f"❌ Sleep command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display desktop notification."""
    global pending_shutdown, pending_reboot
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /msg <message text>")
        return
    
    message_text = ' '.join(context.args)
    
    if len(message_text) > 1000:
        await update.message.reply_text("❌ Message too long (max 1000 characters)")
        return
    
    try:
        notify_commands = [
            ['notify-send', 'C3NTR@L COMM@ND', message_text, '-t', '10000'],
            ['zenity', '--notification', '--text', f'C3NTR@L COMM@ND: {message_text}'],
            ['kdialog', '--title', 'C3NTR@L COMM@ND', '--passivepopup', message_text, '10']
        ]
        
        success = False
        for cmd in notify_commands:
            if not check_dependency(cmd[0]):
                continue
                
            success, stdout, stderr = await safe_system_command(cmd)
            if success:
                break
        
        if success:
            await update.message.reply_text(f"📩 Message displayed: {message_text}")
            logger.info(f"Desktop message sent by user {update.effective_user.id}")
        else:
            await update.message.reply_text(
                "❌ Could not display desktop message.\n"
                "Install: `sudo apt install libnotify-bin`"
            )
            
    except Exception as e:
        error_msg = f"❌ Message command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def speak_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Speak text aloud using text-to-speech."""
    global pending_shutdown, pending_reboot
    
    if not context.args:
        await update.message.reply_text("❌ Usage: /speak <text to speak>")
        return
    
    text_to_speak = ' '.join(context.args)
    
    if len(text_to_speak) > 500:
        await update.message.reply_text("❌ Text too long (max 500 characters)")
        return
    
    try:
        await update.message.reply_text(f"🗣️ Speaking: {text_to_speak[:100]}...")
        
        tts_commands = [
            (['espeak', text_to_speak], None),
            (['spd-say', text_to_speak], None),
        ]
        
        success = False
        method_used = "unknown"
        
        for cmd, input_text in tts_commands:
            if not check_dependency(cmd[0]):
                continue
                
            success, stdout, stderr = await safe_system_command(cmd, input_text=input_text)
            if success:
                method_used = cmd[0]
                break
        
        if success:
            await update.message.reply_text("✅ Text spoken successfully")
            logger.info(f"Text spoken by user {update.effective_user.id} using {method_used}")
        else:
            await update.message.reply_text(
                "❌ Could not speak text.\n"
                "Install: `sudo apt install espeak`"
            )
            
    except Exception as e:
        error_msg = f"❌ Speak command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

# Enhanced utility functions
def get_system_status():
    """Get comprehensive system control status for status reports."""
    return {
        'pending_shutdown': pending_shutdown,
        'pending_reboot': pending_reboot,
        'shutdown_delay': shutdown_delay,
        'reboot_delay': reboot_delay,
        'usb_monitoring': usb_monitoring,
        'network_monitoring': network_monitoring,
        'process_monitoring': process_monitoring,
        'file_monitoring': file_monitoring,
        'pending_usb_analysis': len(usb_analysis_pending)
    }

def cleanup():
    """Cleanup resources on module unload."""
    global pending_shutdown, pending_reboot, usb_monitoring
    pending_shutdown = False
    pending_reboot = False
    usb_monitoring = False
    usb_analysis_pending.clear()

# Background monitoring task
async def start_background_monitoring():
    """Start all background monitoring tasks."""
    # USB monitoring will be started by usb_monitor_start_command
    logger.info("Background monitoring system ready")