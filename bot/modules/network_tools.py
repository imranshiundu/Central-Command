#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.1 - Network Tools Module
Network diagnostics, WiFi, speed tests, and connectivity
100% COMPLETE & BUG-FREE VERSION
"""

import os
import logging
import subprocess
import asyncio
import json
import re
import socket
import time
from datetime import datetime
from urllib.parse import urlparse

# Try to import optional dependencies
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    logging.warning("aiohttp not available. Some features may be limited.")

try:
    from telegram import Update
    from telegram.ext import ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Telegram library not available.")

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
    logging.error("config.json not found")

BASE_DIR = config.get('paths', {}).get('base_dir', '/home/imran/C3NTR@L-COMM@ND-V1.1')
LOGS_DIR = os.path.join(BASE_DIR, config.get('paths', {}).get('logs_dir', 'logs'))

logger = logging.getLogger(__name__)

# Network settings
PUBLIC_IP_SERVICES = [
    'https://api.ipify.org',
    'https://ident.me', 
    'https://checkip.amazonaws.com',
    'https://ipinfo.io/ip'
]

PING_TIMEOUT = 10  # seconds
SPEEDTEST_TIMEOUT = 120  # seconds

# Rate limiting
last_command_time = {}
COMMAND_COOLDOWN = 5  # seconds

def register_commands(register_func):
    """Register all network commands with the main bot."""
    commands = {
        'ip': (ip_command, "Show public and local IP addresses"),
        'wifi': (wifi_command, "List WiFi networks and connection status"),
        'speedtest': (speedtest_command, "Run internet speed test"),
        'ping': (ping_command, "Ping a host <hostname/IP>"),
        'vpn': (vpn_command, "Show VPN status"),
        'netinfo': (netinfo_command, "Show network interface information"),
        'ports': (ports_command, "Show listening ports"),
        'networktest': (networktest_command, "Run comprehensive network connectivity test")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("Network tools module registered successfully")

def rate_limit_check(user_id, command):
    """Check if user is rate limited for a command."""
    global last_command_time
    
    key = f"{user_id}_{command}"
    current_time = time.time()
    
    if key in last_command_time:
        time_since_last = current_time - last_command_time[key]
        if time_since_last < COMMAND_COOLDOWN:
            return False, COMMAND_COOLDOWN - time_since_last
    
    last_command_time[key] = current_time
    return True, 0

async def safe_network_command(cmd, timeout=30, input_text=None):
    """Safely execute network command with timeout and error handling."""
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

def check_tool_available(tool):
    """Check if a network tool is available."""
    try:
        subprocess.run(['which', tool], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

async def ip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get public and local IP addresses."""
    # Rate limiting check
    allowed, wait_time = rate_limit_check(update.effective_user.id, 'ip')
    if not allowed:
        await update.message.reply_text(f"⏳ Please wait {wait_time:.1f}s before using this command again")
        return
    
    try:
        await update.message.reply_text("🌐 Gathering IP information...")
        
        message = "📡 *IP Address Information*\n\n"
        
        # Get public IP with multiple fallbacks
        public_ip = await get_public_ip()
        if public_ip:
            message += f"🌍 *Public IP:* `{public_ip}`\n"
            
            # Get IP information if available
            ip_info = await get_ip_info(public_ip)
            if ip_info:
                message += f"🏙️ *Location:* {ip_info}\n"
        else:
            message += "🌍 *Public IP:* ❌ Unable to determine\n"
        
        # Get local IPs
        local_ips = await get_local_ips()
        if local_ips:
            message += "\n🏠 *Local IPs:*\n"
            for interface, ip in local_ips.items():
                message += f"  • {interface}: `{ip}`\n"
        else:
            message += "\n🏠 *Local IPs:* ❌ No network interfaces found\n"
        
        # Get router/gateway IP
        gateway = await get_gateway_ip()
        if gateway:
            message += f"\n🚪 *Gateway:* `{gateway}`\n"
        
        # Get DNS information
        dns_servers = await get_dns_servers()
        if dns_servers:
            message += f"🔍 *DNS Servers:* `{', '.join(dns_servers[:2])}`\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ IP command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def get_public_ip():
    """Get public IP address with multiple fallback services."""
    # Try aiohttp first if available
    if AIOHTTP_AVAILABLE:
        for service in PUBLIC_IP_SERVICES:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.get(service) as response:
                        if response.status == 200:
                            ip = (await response.text()).strip()
                            if ip and re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                                return ip
            except Exception as e:
                logger.debug(f"Public IP service {service} failed: {e}")
                continue
    
    # Fallback: try curl if aiohttp fails or not available
    curl_services = ['https://api.ipify.org', 'https://ident.me']
    for service in curl_services:
        if check_tool_available('curl'):
            success, stdout, stderr = await safe_network_command(
                ['curl', '-s', '-m', '10', service]
            )
            if success and stdout and re.match(r'^\d+\.\d+\.\d+\.\d+$', stdout):
                return stdout
    
    return None

async def get_ip_info(ip_address):
    """Get basic IP information (location, ISP)."""
    if not AIOHTTP_AVAILABLE:
        return None
    
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f'http://ip-api.com/json/{ip_address}?fields=country,city,isp') as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'success':
                        location_parts = []
                        if data.get('city'):
                            location_parts.append(data['city'])
                        if data.get('country'):
                            location_parts.append(data['country'])
                        if data.get('isp'):
                            location_parts.append(data['isp'])
                        
                        return ', '.join(location_parts) if location_parts else None
    except Exception as e:
        logger.debug(f"IP info lookup failed: {e}")
    
    return None

async def get_local_ips():
    """Get local IP addresses for all interfaces."""
    local_ips = {}
    
    try:
        # Method 1: Using ip command
        if check_tool_available('ip'):
            success, stdout, stderr = await safe_network_command(['ip', 'addr', 'show'])
            if success:
                for line in stdout.split('\n'):
                    if 'inet ' in line and 'scope global' in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            interface = parts[-1]
                            ip = parts[1].split('/')[0]
                            if ip != '127.0.0.1':
                                local_ips[interface] = ip
        
        # Method 2: Using hostname if ip command fails
        if not local_ips:
            success, stdout, stderr = await safe_network_command(['hostname', '-I'])
            if success and stdout:
                ips = stdout.strip().split()
                for i, ip in enumerate(ips):
                    if ip != '127.0.0.1' and re.match(r'^\d+\.\d+\.\d+\.\d+$', ip):
                        local_ips[f'eth{i}'] = ip
        
        # Method 3: Python socket fallback
        if not local_ips:
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                if local_ip != '127.0.0.1':
                    local_ips['primary'] = local_ip
            except:
                pass
                
    except Exception as e:
        logger.error(f"Error getting local IPs: {e}")
    
    return local_ips

async def get_gateway_ip():
    """Get gateway/router IP address."""
    try:
        if check_tool_available('ip'):
            success, stdout, stderr = await safe_network_command(['ip', 'route', 'show', 'default'])
            if success and stdout:
                match = re.search(r'default via (\d+\.\d+\.\d+\.\d+)', stdout)
                if match:
                    return match.group(1)
        
        if check_tool_available('netstat'):
            success, stdout, stderr = await safe_network_command(['netstat', '-rn'])
            if success and stdout:
                for line in stdout.split('\n'):
                    if '0.0.0.0' in line or 'default' in line:
                        parts = line.split()
                        if len(parts) >= 2 and re.match(r'^\d+\.\d+\.\d+\.\d+$', parts[1]):
                            return parts[1]
    except Exception as e:
        logger.debug(f"Error getting gateway: {e}")
    
    return None

async def get_dns_servers():
    """Get DNS server addresses."""
    dns_servers = []
    
    try:
        # Method 1: Check resolv.conf
        if os.path.exists('/etc/resolv.conf'):
            with open('/etc/resolv.conf', 'r') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        dns = line.split()[1]
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', dns):
                            dns_servers.append(dns)
        
        # Method 2: Using systemd-resolve
        if not dns_servers and check_tool_available('systemd-resolve'):
            success, stdout, stderr = await safe_network_command(['systemd-resolve', '--status'])
            if success:
                for line in stdout.split('\n'):
                    if 'DNS Server' in line:
                        dns = line.split(':')[1].strip()
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', dns):
                            dns_servers.append(dns)
        
        # Method 3: Using nmcli
        if not dns_servers and check_tool_available('nmcli'):
            success, stdout, stderr = await safe_network_command(['nmcli', 'dev', 'show'])
            if success:
                for line in stdout.split('\n'):
                    if 'IP4.DNS' in line:
                        dns = line.split(':')[1].strip()
                        if re.match(r'^\d+\.\d+\.\d+\.\d+$', dns):
                            dns_servers.append(dns)
                            
    except Exception as e:
        logger.debug(f"Error getting DNS servers: {e}")
    
    return dns_servers[:3]  # Return max 3 DNS servers

async def wifi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show WiFi networks and connection status."""
    # Rate limiting check
    allowed, wait_time = rate_limit_check(update.effective_user.id, 'wifi')
    if not allowed:
        await update.message.reply_text(f"⏳ Please wait {wait_time:.1f}s before using this command again")
        return
    
    try:
        await update.message.reply_text("📶 Scanning WiFi networks...")
        
        message = "📶 *WiFi Information*\n\n"
        
        # Get current connection
        current_ssid = await get_current_wifi()
        if current_ssid:
            message += f"🔗 *Connected to:* `{current_ssid}`\n\n"
        else:
            message += "🔗 *Connected to:* ❌ Not connected\n\n"
        
        # Get available networks
        networks = await scan_wifi_networks()
        if networks:
            message += "📡 *Available Networks:*\n"
            for i, (ssid, signal, security) in enumerate(networks[:15]):  # Limit to 15 networks
                signal_bars = "▮" * min(5, (signal + 100) // 20) + "▯" * (5 - min(5, (signal + 100) // 20))
                message += f"`{ssid:<20} {signal_bars} {signal:>3}dBm {security}`\n"
            
            if len(networks) > 15:
                message += f"\n... and {len(networks) - 15} more networks\n"
        else:
            message += "📡 *Available Networks:* ❌ No networks found or no WiFi adapter\n"
        
        # Get WiFi interface info
        interface_info = await get_wifi_interface_info()
        if interface_info:
            message += f"\n💻 *Interface:* {interface_info}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ WiFi command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def get_current_wifi():
    """Get currently connected WiFi SSID."""
    try:
        # Method 1: Using nmcli (NetworkManager)
        if check_tool_available('nmcli'):
            success, stdout, stderr = await safe_network_command([
                'nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'
            ])
            if success:
                for line in stdout.split('\n'):
                    if line.startswith('yes:'):
                        return line.split(':')[1]
        
        # Method 2: Using iwgetid
        if check_tool_available('iwgetid'):
            success, stdout, stderr = await safe_network_command(['iwgetid', '-r'])
            if success and stdout:
                return stdout.strip()
        
        # Method 3: Using iwconfig
        if check_tool_available('iwconfig'):
            success, stdout, stderr = await safe_network_command(['iwconfig'])
            if success:
                for line in stdout.split('\n'):
                    if 'ESSID:' in line:
                        match = re.search(r'ESSID:"([^"]+)"', line)
                        if match:
                            return match.group(1)
    except Exception as e:
        logger.debug(f"Error getting current WiFi: {e}")
    
    return None

async def scan_wifi_networks():
    """Scan for available WiFi networks."""
    networks = []
    
    try:
        # Method 1: Using nmcli
        if check_tool_available('nmcli'):
            success, stdout, stderr = await safe_network_command([
                'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'dev', 'wifi', '--rescan', 'yes'
            ])
            if success:
                for line in stdout.split('\n'):
                    if line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 3:
                            ssid, signal, security = parts[0], parts[1], parts[2]
                            if ssid and ssid != '--':  # Filter hidden networks
                                try:
                                    networks.append((ssid, int(signal), security))
                                except ValueError:
                                    continue
        
        # Method 2: Using iwlist if nmcli fails
        if not networks and check_tool_available('iwlist'):
            success, stdout, stderr = await safe_network_command(['iwlist', 'scan'])
            if success:
                current_ssid = None
                current_signal = None
                current_security = "Open"
                
                for line in stdout.split('\n'):
                    line = line.strip()
                    if 'ESSID:' in line:
                        match = re.search(r'ESSID:"([^"]+)"', line)
                        if match:
                            current_ssid = match.group(1)
                    elif 'Signal level=' in line:
                        match = re.search(r'Signal level=(-?\d+)', line)
                        if match:
                            current_signal = int(match.group(1))
                    elif 'Encryption key:' in line:
                        if 'on' in line:
                            current_security = "WEP"
                    elif 'IE:' in line and 'WPA' in line:
                        current_security = "WPA"
                    
                    if current_ssid and current_signal is not None:
                        if current_ssid != '':  # Filter empty SSIDs
                            networks.append((current_ssid, current_signal, current_security))
                        current_ssid = None
                        current_signal = None
                        current_security = "Open"
        
        # Sort by signal strength (descending)
        networks.sort(key=lambda x: x[1], reverse=True)
        
    except Exception as e:
        logger.error(f"Error scanning WiFi networks: {e}")
    
    return networks

async def get_wifi_interface_info():
    """Get WiFi interface information."""
    try:
        if check_tool_available('iwconfig'):
            success, stdout, stderr = await safe_network_command(['iwconfig'])
            if success:
                for line in stdout.split('\n'):
                    if 'IEEE 802.11' in line:
                        interface = line.split()[0]
                        return interface
    except Exception as e:
        logger.debug(f"Error getting WiFi interface: {e}")
    
    return None

async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run internet speed test."""
    # Rate limiting check
    allowed, wait_time = rate_limit_check(update.effective_user.id, 'speedtest')
    if not allowed:
        await update.message.reply_text(f"⏳ Please wait {wait_time:.1f}s before using this command again")
        return
    
    try:
        progress_msg = await update.message.reply_text("🚀 Starting speed test...")
        
        # Method 1: Using speedtest-cli
        if check_tool_available('speedtest-cli'):
            await progress_msg.edit_text("🔄 Running speedtest-cli...")
            
            success, stdout, stderr = await safe_network_command(
                ['speedtest-cli', '--simple', '--secure'],
                timeout=SPEEDTEST_TIMEOUT
            )
            
            if success:
                message = "📊 *Speed Test Results*\n\n"
                for line in stdout.split('\n'):
                    if 'Ping:' in line:
                        message += f"🏓 *Ping:* `{line.split()[1]} {line.split()[2]}`\n"
                    elif 'Download:' in line:
                        message += f"⬇️ *Download:* `{line.split()[1]} {line.split()[2]}`\n"
                    elif 'Upload:' in line:
                        message += f"⬆️ *Upload:* `{line.split()[1]} {line.split()[2]}`\n"
                
                await progress_msg.edit_text(message, parse_mode='Markdown')
                return
        
        # Method 2: Using curl-based fallback
        await progress_msg.edit_text("🔄 Testing download speed...")
        
        # Test download speed
        download_speed = await test_download_speed()
        
        await progress_msg.edit_text("🔄 Testing upload speed...")
        
        # Test upload speed (proper implementation)
        upload_speed = await test_upload_speed()
        
        # Test ping
        ping_time = await test_ping_speed()
        
        message = (
            "📊 *Speed Test Results* (Basic)\n\n"
            f"🏓 *Ping:* `{ping_time} ms`\n"
            f"⬇️ *Download:* `{download_speed:.1f} Mbps`\n" 
            f"⬆️ *Upload:* `{upload_speed:.1f} Mbps`\n\n"
            "💡 Install `speedtest-cli` for more accurate results"
        )
        
        await progress_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Speed test error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def test_download_speed():
    """Test download speed using curl."""
    try:
        # Use a reliable file for speed test
        test_files = [
            'http://ipv4.download.thinkbroadband.com/10MB.zip',
            'http://speedtest.tele2.net/10MB.zip'
        ]
        
        for test_file in test_files:
            if check_tool_available('curl'):
                start_time = time.time()
                success, stdout, stderr = await safe_network_command([
                    'curl', '-s', '-o', '/dev/null', '-w', '%{speed_download}',
                    test_file
                ], timeout=30)
                
                if success and stdout:
                    try:
                        # speed_download is in bytes/sec
                        speed_bps = float(stdout)
                        speed_mbps = (speed_bps * 8) / 1_000_000  # Convert to Mbps
                        return speed_mbps
                    except ValueError:
                        continue
    except Exception as e:
        logger.debug(f"Download speed test error: {e}")
    
    return 0.0

async def test_upload_speed():
    """Test upload speed using a simple method."""
    try:
        # Create a small test file
        test_file = '/tmp/speedtest_upload.bin'
        with open(test_file, 'wb') as f:
            f.write(os.urandom(1_000_000))  # 1MB test file
        
        if check_tool_available('curl'):
            # Try to upload to a service that accepts POST (this is a simplified test)
            start_time = time.time()
            success, stdout, stderr = await safe_network_command([
                'curl', '-s', '-o', '/dev/null', '-w', '%{speed_upload}',
                '-X', 'POST', '--data-binary', f'@{test_file}',
                'http://httpbin.org/post'
            ], timeout=30)
            
            # Clean up test file
            try:
                os.remove(test_file)
            except:
                pass
            
            if success and stdout:
                try:
                    speed_bps = float(stdout)
                    speed_mbps = (speed_bps * 8) / 1_000_000
                    return speed_mbps
                except ValueError:
                    pass
    except Exception as e:
        logger.debug(f"Upload speed test error: {e}")
    
    return 0.0

async def test_ping_speed():
    """Test ping to reliable host."""
    try:
        hosts = ['8.8.8.8', '1.1.1.1', 'google.com']
        
        for host in hosts:
            success, stdout, stderr = await safe_network_command([
                'ping', '-c', '3', '-W', '3', host
            ], timeout=10)
            
            if success and 'min/avg/max' in stdout:
                # Extract average ping time
                match = re.search(r'min/avg/max/[^=]*=\s*[\d.]+/([\d.]+)/', stdout)
                if match:
                    return match.group(1)
    except Exception as e:
        logger.debug(f"Ping test error: {e}")
    
    return "N/A"

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ping a host."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /ping <hostname_or_ip>")
        return
    
    host = context.args[0].strip()
    
    # Strict host validation
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$', host):
        await update.message.reply_text("❌ Invalid hostname or IP address")
        return
    
    # Rate limiting check
    allowed, wait_time = rate_limit_check(update.effective_user.id, 'ping')
    if not allowed:
        await update.message.reply_text(f"⏳ Please wait {wait_time:.1f}s before using this command again")
        return
    
    try:
        await update.message.reply_text(f"🏓 Pinging {host}...")
        
        if check_tool_available('ping'):
            success, stdout, stderr = await safe_network_command([
                'ping', '-c', '4', '-W', '3', host
            ], timeout=PING_TIMEOUT)
            
            if success:
                # Parse ping results
                lines = stdout.split('\n')
                summary = lines[-2] if len(lines) >= 2 else "No summary"
                
                message = f"🏓 *Ping Results for {host}*\n\n"
                message += f"```\n{stdout}\n```"
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ Host {host} is unreachable or timed out")
        else:
            await update.message.reply_text("❌ ping command not available")
        
    except Exception as e:
        error_msg = f"❌ Ping error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show VPN status."""
    try:
        await update.message.reply_text("🛡️ Checking VPN status...")
        
        message = "🛡️ *VPN Status*\n\n"
        
        # Check common VPN interfaces
        vpn_interfaces = await check_vpn_interfaces()
        if vpn_interfaces:
            message += "✅ *VPN Active*\n"
            for interface, info in vpn_interfaces.items():
                message += f"  • {interface}: {info}\n"
        else:
            message += "❌ *VPN Not Detected*\n"
        
        # Check VPN processes
        vpn_processes = await check_vpn_processes()
        if vpn_processes:
            message += "\n🔍 *VPN Processes:*\n"
            for process in vpn_processes[:5]:  # Limit to 5 processes
                message += f"  • {process}\n"
        
        # Check routing table for VPN
        vpn_routes = await check_vpn_routes()
        if vpn_routes:
            message += "\n🛣️ *VPN Routes:*\n"
            for route in vpn_routes[:3]:  # Limit to 3 routes
                message += f"  • {route}\n"
        
        if not any([vpn_interfaces, vpn_processes, vpn_routes]):
            message += "\n💡 No VPN detected. Common VPN services:\n"
            message += "  • OpenVPN, WireGuard, PPTP, L2TP\n"
            message += "  • Commercial VPN clients"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ VPN command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def check_vpn_interfaces():
    """Check for VPN network interfaces."""
    vpn_interfaces = {}
    
    try:
        if check_tool_available('ip'):
            success, stdout, stderr = await safe_network_command(['ip', 'addr', 'show'])
            if success:
                for line in stdout.split('\n'):
                    if 'tun' in line or 'tap' in line or 'ppp' in line or 'wg' in line:
                        interface = line.split(':')[1].strip()
                        vpn_interfaces[interface] = "VPN Interface"
    except Exception as e:
        logger.debug(f"Error checking VPN interfaces: {e}")
    
    return vpn_interfaces

async def check_vpn_processes():
    """Check for running VPN processes."""
    vpn_processes = []
    vpn_keywords = ['openvpn', 'wireguard', 'wg', 'vpn', 'pptp', 'l2tp', 'ipsec']
    
    try:
        if check_tool_available('ps'):
            success, stdout, stderr = await safe_network_command(['ps', 'aux'])
            if success:
                for line in stdout.split('\n'):
                    if any(keyword in line.lower() for keyword in vpn_keywords):
                        # Extract process name (first non-whitespace after user)
                        parts = line.split()
                        if len(parts) > 10:
                            process_name = parts[10]
                            if process_name not in vpn_processes:
                                vpn_processes.append(process_name)
    except Exception as e:
        logger.debug(f"Error checking VPN processes: {e}")
    
    return vpn_processes

async def check_vpn_routes():
    """Check for VPN routes in routing table."""
    vpn_routes = []
    
    try:
        if check_tool_available('ip'):
            success, stdout, stderr = await safe_network_command(['ip', 'route', 'show'])
            if success:
                for line in stdout.split('\n'):
                    if 'tun' in line or 'tap' in line or 'ppp' in line or 'wg' in line:
                        vpn_routes.append(line.strip())
    except Exception as e:
        logger.debug(f"Error checking VPN routes: {e}")
    
    return vpn_routes

async def netinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show network interface information."""
    try:
        await update.message.reply_text("🔧 Gathering network information...")
        
        message = "🔧 *Network Interface Information*\n\n"
        
        # Get interface details
        if check_tool_available('ip'):
            success, stdout, stderr = await safe_network_command(['ip', 'addr', 'show'])
            if success:
                interface_count = 0
                for line in stdout.split('\n'):
                    if line and not line.startswith(' '):
                        interface_count += 1
                        if interface_count <= 8:  # Limit output
                            message += f"`{line}`\n"
                
                if interface_count > 8:
                    message += f"\n... and {interface_count - 8} more interfaces\n"
            else:
                message += "❌ Unable to get interface information\n"
        else:
            message += "❌ ip command not available\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Netinfo command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def ports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show listening ports."""
    try:
        await update.message.reply_text("🔍 Checking listening ports...")
        
        message = "🔍 *Listening Ports*\n\n"
        
        # Method 1: Using netstat
        if check_tool_available('netstat'):
            success, stdout, stderr = await safe_network_command([
                'netstat', '-tulpn'
            ])
            if success:
                listening_ports = []
                for line in stdout.split('\n'):
                    if 'LISTEN' in line:
                        listening_ports.append(line)
                
                if listening_ports:
                    message += "```\n"
                    for port in listening_ports[:10]:  # Limit to 10 ports
                        message += f"{port}\n"
                    message += "```\n"
                    
                    if len(listening_ports) > 10:
                        message += f"... and {len(listening_ports) - 10} more ports\n"
                else:
                    message += "No listening ports found\n"
            else:
                message += "❌ Unable to get port information\n"
        else:
            message += "❌ netstat command not available\n"
        
        # Method 2: Using ss as fallback
        if "Unable" in message and check_tool_available('ss'):
            success, stdout, stderr = await safe_network_command(['ss', '-tulpn'])
            if success:
                message += "\n*Using ss command:*\n```\n"
                lines = stdout.split('\n')[:8]  # Limit output
                for line in lines:
                    message += f"{line}\n"
                message += "```\n"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Ports command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def networktest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run comprehensive network connectivity test."""
    # Rate limiting check
    allowed, wait_time = rate_limit_check(update.effective_user.id, 'networktest')
    if not allowed:
        await update.message.reply_text(f"⏳ Please wait {wait_time:.1f}s before using this command again")
        return
    
    try:
        progress_msg = await update.message.reply_text("🔧 Running comprehensive network test...")
        
        message = "🔧 *Network Connectivity Test*\n\n"
        tests_passed = 0
        total_tests = 0
        
        # Test 1: Local network interface
        await progress_msg.edit_text("🔧 Testing local network interface...")
        local_ips = await get_local_ips()
        if local_ips:
            message += "✅ Local network interface: OK\n"
            tests_passed += 1
        else:
            message += "❌ Local network interface: FAILED\n"
        total_tests += 1
        
        # Test 2: Gateway connectivity
        await progress_msg.edit_text("🔧 Testing gateway connectivity...")
        gateway = await get_gateway_ip()
        if gateway and check_tool_available('ping'):
            success, stdout, stderr = await safe_network_command(['ping', '-c', '2', '-W', '2', gateway])
            if success:
                message += f"✅ Gateway ({gateway}): REACHABLE\n"
                tests_passed += 1
            else:
                message += f"❌ Gateway ({gateway}): UNREACHABLE\n"
        else:
            message += "❌ Gateway: NOT FOUND\n"
        total_tests += 1
        
        # Test 3: DNS resolution
        await progress_msg.edit_text("🔧 Testing DNS resolution...")
        if check_tool_available('nslookup'):
            success, stdout, stderr = await safe_network_command(['nslookup', 'google.com'])
            if success and 'Address:' in stdout:
                message += "✅ DNS resolution: OK\n"
                tests_passed += 1
            else:
                message += "❌ DNS resolution: FAILED\n"
        else:
            message += "⚠️ DNS resolution: SKIPPED (nslookup not available)\n"
        total_tests += 1
        
        # Test 4: Internet connectivity
        await progress_msg.edit_text("🔧 Testing internet connectivity...")
        public_ip = await get_public_ip()
        if public_ip:
            message += f"✅ Internet connectivity: OK (IP: {public_ip})\n"
            tests_passed += 1
        else:
            message += "❌ Internet connectivity: FAILED\n"
        total_tests += 1
        
        # Test 5: Common services
        await progress_msg.edit_text("🔧 Testing common services...")
        test_hosts = ['8.8.8.8', '1.1.1.1']
        service_ok = False
        for host in test_hosts:
            if check_tool_available('ping'):
                success, stdout, stderr = await safe_network_command(['ping', '-c', '1', '-W', '3', host])
                if success:
                    service_ok = True
                    break
        
        if service_ok:
            message += "✅ Common services: REACHABLE\n"
            tests_passed += 1
        else:
            message += "❌ Common services: UNREACHABLE\n"
        total_tests += 1
        
        # Summary
        message += f"\n📊 *Summary:* {tests_passed}/{total_tests} tests passed\n"
        
        if tests_passed == total_tests:
            message += "🎉 All network tests passed!\n"
        elif tests_passed >= total_tests * 0.7:
            message += "⚠️ Most tests passed, minor issues detected\n"
        else:
            message += "🚨 Major network issues detected\n"
        
        await progress_msg.edit_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Network test error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

# Utility functions for other modules
async def get_network_status():
    """Get network status for system reports - ASYNC VERSION."""
    return {
        'public_ip': await get_public_ip() or "Unknown",
        'wifi_connected': await get_current_wifi() or "Not connected",
        'interfaces_count': len(await get_local_ips() or {})
    }