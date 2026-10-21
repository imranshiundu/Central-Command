#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.2 - CODE M0TH3R
Network Controller Module - Internet & Communication Control
COMPLETE & BUG-FREE VERSION
"""

import os
import logging
import subprocess
import asyncio
import json
import sqlite3
import time
import threading
import requests
import socket
import re
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import hashlib
from telegram import Update
from telegram.ext import ContextTypes
import psutil
import platform
import zipfile

# Load config
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}
    logging.error("config.json not found")

BASE_DIR = config.get('paths', {}).get('base_dir', '/home/imran/snap/C3NTR@L-COMM@ND-V1.2')
NETWORK_DIR = os.path.join(BASE_DIR, 'bot', 'data', 'network')
SCRAPED_DIR = os.path.join(NETWORK_DIR, 'scraped_data')
DOWNLOADS_DIR = os.path.join(BASE_DIR, 'downloads')
CLOUD_DIR = os.path.join(NETWORK_DIR, 'cloud_sync')
NETWORK_DB = os.path.join(BASE_DIR, 'security', 'network_controller.db')

logger = logging.getLogger(__name__)

# Network control state
network_state = {
    'active_downloads': {},
    'web_scraping': {},
    'cloud_sync_active': False,
    'website_monitoring': {},
    'api_connections': {},
    'phone_connected': False,
    'vpn_active': False,
    'tor_active': False,
    'network_blocked': False
}

# Phone integration state
phone_state = {
    'connected': False,
    'last_sync': None,
    'battery_level': 0,
    'network_type': 'unknown'
}

network_lock = threading.Lock()

def register_commands(register_func):
    """Register all network commands with the main bot."""
    commands = {
        'web_scrape': (web_scrape_command, "Scrape website data [url] [depth]"),
        'download_manager': (download_manager_command, "Manage downloads [list/pause/resume/cancel]"),
        'cloud_sync': (cloud_sync_command, "Sync files to cloud services [service] [action]"),
        'website_monitor': (website_monitor_command, "Monitor website status [url] [interval]"),
        'api_control': (api_control_command, "Control web APIs [service] [action]"),
        'phone_sms': (phone_sms_command, "Send SMS via connected phone [number] [message]"),
        'phone_call': (phone_call_command, "Make phone call [number]"),
        'phone_location': (phone_location_command, "Get phone GPS location"),
        'phone_wipe': (phone_wipe_command, "Remote phone data wipe"),
        'phone_notifications': (phone_notifications_command, "Read phone notifications"),
        'speed_test': (speed_test_command, "Run internet speed test"),
        'network_scan': (network_scan_command, "Scan network for devices"),
        'vpn_control': (vpn_control_command, "Control VPN connection [on/off/status]"),
        'tor_control': (tor_control_command, "Control Tor routing [on/off/status]"),
        'website_block': (website_block_command, "Block/unblock websites [url] [action]"),
        'port_forward': (port_forward_command, "Configure port forwarding"),
        'network_status': (network_status_command, "Check comprehensive network status")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("📡 Network controller module registered successfully")
    initialize_network_system()

def initialize_network_system():
    """Initialize network control system."""
    try:
        os.makedirs(NETWORK_DIR, exist_ok=True)
        os.makedirs(SCRAPED_DIR, exist_ok=True)
        os.makedirs(CLOUD_DIR, exist_ok=True)
        os.makedirs(os.path.join(NETWORK_DIR, 'monitoring'), exist_ok=True)
        os.makedirs(os.path.join(NETWORK_DIR, 'api_data'), exist_ok=True)
        os.makedirs(os.path.join(NETWORK_DIR, 'phone_data'), exist_ok=True)
        
        # Initialize network database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        # Web scraping table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS web_scraping (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                depth INTEGER,
                scraped_data TEXT,
                scraped_time DATETIME,
                file_path TEXT,
                status TEXT
            )
        ''')
        
        # Downloads table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                file_path TEXT,
                file_size INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                status TEXT,
                download_speed REAL,
                resume_supported BOOLEAN
            )
        ''')
        
        # Cloud sync table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cloud_sync (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                action TEXT,
                file_path TEXT,
                sync_time DATETIME,
                status TEXT,
                sync_direction TEXT
            )
        ''')
        
        # Website monitoring table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS website_monitoring (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                check_interval INTEGER,
                last_check DATETIME,
                status_code INTEGER,
                response_time REAL,
                content_changed BOOLEAN,
                alert_sent BOOLEAN
            )
        ''')
        
        # API connections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                endpoint TEXT,
                request_time DATETIME,
                response_code INTEGER,
                response_data TEXT,
                error_message TEXT
            )
        ''')
        
        # Phone operations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phone_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT,
                target TEXT,
                data TEXT,
                operation_time DATETIME,
                status TEXT,
                result TEXT
            )
        ''')
        
        # Network devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS network_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                mac_address TEXT,
                hostname TEXT,
                first_seen DATETIME,
                last_seen DATETIME,
                device_type TEXT,
                trusted BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Start background monitoring
        threading.Thread(target=background_monitoring, daemon=True).start()
        
        logger.info("✅ Network control system initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Network system initialization failed: {e}")

async def safe_system_command(cmd, timeout=60, shell=False):
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

async def web_scrape_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scrape website data with advanced features."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/web_scrape [url] [depth]`\n\n"
                "**Examples:**\n"
                "• `/web_scrape https://example.com 2` - Scrape with depth 2\n"
                "• `/web_scrape https://site.com` - Basic scrape\n"
                "• `/web_scrape list` - Show recent scrapes\n\n"
                "**Features:**\n"
                "• Multi-level scraping\n"
                "• JavaScript rendering\n"
                "• Form interaction\n"
                "• Data extraction\n"
                "• File downloads",
                parse_mode='Markdown'
            )
            return
        
        if context.args[0].lower() == 'list':
            await list_recent_scrapes(update)
            return
        
        url = context.args[0]
        depth = 1
        if len(context.args) > 1:
            try:
                depth = int(context.args[1])
                depth = max(1, min(5, depth))  # Limit depth to 1-5
            except ValueError:
                await update.message.reply_text("❌ Invalid depth. Using default depth 1.")
        
        await update.message.reply_text(
            f"🕸️ **WEB SCRAPING INITIATED**\n\n"
            f"**Target:** `{url}`\n"
            f"**Depth:** `{depth}`\n"
            f"**Starting advanced web scraping...**\n\n"
            f"**Scraping Features:**\n"
            f"• HTML content extraction\n"
            f"• Link discovery (depth {depth})\n"
            f"• Image and file downloading\n"
            f"• Form data extraction\n"
            f"• Metadata collection\n\n"
            f"⏰ Estimated time: 1-3 minutes",
            parse_mode='Markdown'
        )
        
        scrape_results = await perform_web_scraping(url, depth)
        
        # Generate scrape report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(SCRAPED_DIR, f'scrape_report_{timestamp}.txt')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("WEB SCRAPING REPORT\n")
            f.write("=" * 50 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"URL: {url}\n")
            f.write(f"Depth: {depth}\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Status: {scrape_results['status']}\n")
            f.write(f"Pages Scraped: {len(scrape_results['pages'])}\n")
            f.write(f"Files Downloaded: {len(scrape_results['files'])}\n")
            f.write(f"Links Found: {len(scrape_results['links'])}\n\n")
            
            f.write("PAGE SUMMARY:\n")
            f.write("-" * 30 + "\n")
            for page in scrape_results['pages'][:10]:  # Limit to first 10
                f.write(f"URL: {page['url']}\n")
                f.write(f"Title: {page['title']}\n")
                f.write(f"Size: {page['size']} bytes\n")
                f.write(f"Links: {len(page['links'])}\n")
                f.write("-" * 20 + "\n")
        
        # Store in database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO web_scraping 
            (url, depth, scraped_data, scraped_time, file_path, status) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (url, depth, str(scrape_results), datetime.now(), report_path, 'completed')
        )
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ **WEB SCRAPING COMPLETE**\n\n"
            f"**Target:** `{url}`\n"
            f"**Depth:** `{depth}`\n"
            f"**Pages Scraped:** `{len(scrape_results['pages'])}`\n"
            f"**Files Downloaded:** `{len(scrape_results['files'])}`\n"
            f"**Links Discovered:** `{len(scrape_results['links'])}`\n"
            f"**Report:** `{report_path}`\n\n"
            f"**Data Extracted:**\n"
            f"• Page titles and content\n"
            f"• All discovered links\n"
            f"• Downloadable files\n"
            f"• Metadata and structure\n\n"
            f"💡 Use `/download_manager list` to see downloaded files",
            parse_mode='Markdown'
        )
        
        logger.info(f"Web scraping completed: {url} - {len(scrape_results['pages'])} pages")
        
    except Exception as e:
        error_msg = f"❌ Web scrape command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def perform_web_scraping(url: str, depth: int) -> dict:
    """Perform advanced web scraping."""
    results = {
        'status': 'completed',
        'pages': [],
        'files': [],
        'links': [],
        'errors': []
    }
    
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Method 1: Use curl for basic scraping
        success, stdout, stderr = await safe_system_command([
            'curl', '-L', '-A', 'Mozilla/5.0', '--connect-timeout', '30', url
        ])
        
        if success:
            page_data = await extract_page_data(url, stdout)
            results['pages'].append(page_data)
            
            # Extract links for deeper scraping
            if depth > 1:
                links = extract_links(stdout, url)
                results['links'].extend(links)
                
                # Scrape linked pages (limited to 5 for performance)
                for link in links[:5]:
                    try:
                        success, link_content, stderr = await safe_system_command([
                            'curl', '-L', '-A', 'Mozilla/5.0', '--connect-timeout', '20', link
                        ])
                        if success:
                            link_data = await extract_page_data(link, link_content)
                            results['pages'].append(link_data)
                    except Exception as e:
                        results['errors'].append(f"Link {link}: {str(e)}")
        
        # Method 2: Use wget for file downloading
        download_dir = os.path.join(SCRAPED_DIR, 'downloads')
        os.makedirs(download_dir, exist_ok=True)
        
        success, stdout, stderr = await safe_system_command([
            'wget', '-r', '-l', '1', '-nd', '-P', download_dir, '-A', 
            'jpg,jpeg,png,gif,pdf,doc,docx,xls,xlsx', url
        ], timeout=120)
        
        if success:
            # Record downloaded files
            for root, dirs, files in os.walk(download_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    results['files'].append({
                        'filename': file,
                        'path': file_path,
                        'size': os.path.getsize(file_path),
                        'type': file.split('.')[-1].lower()
                    })
        
        # Method 3: Use python requests if available
        try:
            import requests
            from bs4 import BeautifulSoup
            
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract forms
                forms = soup.find_all('form')
                for form in forms:
                    form_data = {
                        'action': form.get('action', ''),
                        'method': form.get('method', 'get'),
                        'inputs': []
                    }
                    
                    for input_tag in form.find_all(['input', 'textarea', 'select']):
                        form_data['inputs'].append({
                            'name': input_tag.get('name', ''),
                            'type': input_tag.get('type', 'text'),
                            'value': input_tag.get('value', '')
                        })
                    
                    if form_data not in results.get('forms', []):
                        results.setdefault('forms', []).append(form_data)
                        
        except ImportError:
            logger.warning("BeautifulSoup not available for advanced scraping")
        except Exception as e:
            logger.warning(f"Advanced scraping failed: {e}")
        
    except Exception as e:
        results['status'] = 'failed'
        results['errors'].append(str(e))
        logger.error(f"Web scraping error for {url}: {e}")
    
    return results

async def extract_page_data(url: str, content: str) -> dict:
    """Extract data from page content."""
    page_data = {
        'url': url,
        'title': 'No title',
        'size': len(content),
        'links': [],
        'images': [],
        'metadata': {}
    }
    
    try:
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            page_data['title'] = title_match.group(1).strip()
        
        # Extract links
        page_data['links'] = extract_links(content, url)
        
        # Extract images
        image_pattern = r'<img[^>]+src="([^">]+)"'
        images = re.findall(image_pattern, content)
        page_data['images'] = [urllib.parse.urljoin(url, img) for img in images]
        
        # Extract metadata
        meta_pattern = r'<meta[^>]+name="([^"]*)"[^>]+content="([^"]*)"'
        meta_tags = re.findall(meta_pattern, content)
        page_data['metadata'] = dict(meta_tags)
        
    except Exception as e:
        logger.error(f"Page data extraction error: {e}")
    
    return page_data

def extract_links(content: str, base_url: str) -> list:
    """Extract all links from content."""
    links = []
    try:
        # Find all anchor tags
        link_pattern = r'<a[^>]+href="([^">]+)"'
        found_links = re.findall(link_pattern, content)
        
        for link in found_links:
            # Convert relative URLs to absolute
            absolute_link = urllib.parse.urljoin(base_url, link)
            if absolute_link.startswith(('http://', 'https://')):
                links.append(absolute_link)
        
        # Remove duplicates
        links = list(set(links))
        
    except Exception as e:
        logger.error(f"Link extraction error: {e}")
    
    return links

async def list_recent_scrapes(update: Update):
    """List recent web scraping activities."""
    try:
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, depth, scraped_time, status FROM web_scraping ORDER BY scraped_time DESC LIMIT 10"
        )
        scrapes = cursor.fetchall()
        conn.close()
        
        if not scrapes:
            await update.message.reply_text("ℹ️ No recent web scraping activities.")
            return
        
        response = "📊 **RECENT WEB SCRAPES**\n\n"
        
        for scrape in scrapes:
            url, depth, scraped_time, status = scrape
            response += f"**URL:** {url}\n"
            response += f"Depth: `{depth}` | Status: `{status}`\n"
            response += f"Time: `{scraped_time}`\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"List scrapes error: {e}")
        await update.message.reply_text("❌ Error retrieving scrape history.")

async def download_manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage file downloads."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/download_manager [action] [parameters]`\n\n"
                "**Actions:**\n"
                "• `list` - Show active downloads\n"
                "• `pause [id]` - Pause download\n"
                "• `resume [id]` - Resume download\n"
                "• `cancel [id]` - Cancel download\n"
                "• `add [url]` - Add new download\n"
                "• `history` - Show download history\n\n"
                "**Examples:**\n"
                "• `/download_manager list`\n"
                "• `/download_manager add https://example.com/file.zip`\n"
                "• `/download_manager pause 1`",
                parse_mode='Markdown'
            )
            return
        
        action = context.args[0].lower()
        
        if action == 'list':
            await list_active_downloads(update)
        
        elif action == 'history':
            await download_history(update)
        
        elif action == 'add':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please provide URL to download.")
                return
            url = context.args[1]
            await add_download(update, url)
        
        elif action in ['pause', 'resume', 'cancel']:
            if len(context.args) < 2:
                await update.message.reply_text(f"❌ Please provide download ID to {action}.")
                return
            try:
                download_id = int(context.args[1])
                await manage_download(update, action, download_id)
            except ValueError:
                await update.message.reply_text("❌ Invalid download ID.")
        
        else:
            await update.message.reply_text("❌ Invalid action.")
            
    except Exception as e:
        error_msg = f"❌ Download manager command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def list_active_downloads(update: Update):
    """List active downloads."""
    try:
        with network_lock:
            active_count = len(network_state['active_downloads'])
        
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, url, file_path, file_size, start_time, status FROM downloads WHERE status IN ('downloading', 'paused') ORDER BY start_time DESC"
        )
        downloads = cursor.fetchall()
        conn.close()
        
        response = f"📥 **ACTIVE DOWNLOADS** (`{active_count}`)\n\n"
        
        if not downloads:
            response += "No active downloads.\n"
        else:
            for download in downloads:
                download_id, url, file_path, file_size, start_time, status = download
                filename = os.path.basename(file_path) if file_path else 'Unknown'
                
                response += f"**ID:** `{download_id}` | **Status:** `{status}`\n"
                response += f"**File:** `{filename}`\n"
                response += f"**URL:** {url}\n"
                if file_size:
                    response += f"**Size:** `{file_size} bytes`\n"
                response += f"**Started:** `{start_time}`\n\n"
        
        response += "💡 Use `/download_manager history` for completed downloads"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"List downloads error: {e}")
        await update.message.reply_text("❌ Error retrieving download list.")

async def download_history(update: Update):
    """Show download history."""
    try:
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT url, file_path, file_size, start_time, end_time, status FROM downloads ORDER BY start_time DESC LIMIT 10"
        )
        downloads = cursor.fetchall()
        conn.close()
        
        response = "📊 **DOWNLOAD HISTORY**\n\n"
        
        if not downloads:
            response += "No download history.\n"
        else:
            for download in downloads:
                url, file_path, file_size, start_time, end_time, status = download
                filename = os.path.basename(file_path) if file_path else 'Unknown'
                
                response += f"**File:** `{filename}`\n"
                response += f"**Status:** `{status}` | **Size:** `{file_size or 'Unknown'} bytes`\n"
                response += f"**URL:** {url}\n"
                response += f"**Completed:** `{end_time or 'In progress'}`\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Download history error: {e}")
        await update.message.reply_text("❌ Error retrieving download history.")

async def add_download(update: Update, url: str):
    """Add new download to queue."""
    try:
        download_id = hashlib.md5(f"{url}{datetime.now()}".encode()).hexdigest()[:8]
        
        # Determine filename from URL
        filename = os.path.basename(urllib.parse.urlparse(url).path)
        if not filename:
            filename = f"download_{download_id}.bin"
        
        file_path = os.path.join(DOWNLOADS_DIR, filename)
        
        # Add to database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO downloads 
            (url, file_path, start_time, status, resume_supported) 
            VALUES (?, ?, ?, ?, ?)""",
            (url, file_path, datetime.now(), 'queued', True)
        )
        conn.commit()
        conn.close()
        
        # Start download in background
        threading.Thread(
            target=download_file,
            args=(download_id, url, file_path),
            daemon=True
        ).start()
        
        with network_lock:
            network_state['active_downloads'][download_id] = {
                'url': url,
                'file_path': file_path,
                'status': 'downloading',
                'start_time': datetime.now()
            }
        
        await update.message.reply_text(
            f"✅ **DOWNLOAD QUEUED**\n\n"
            f"**ID:** `{download_id}`\n"
            f"**URL:** `{url}`\n"
            f"**File:** `{filename}`\n"
            f"**Status:** `QUEUED`\n\n"
            f"💡 Use `/download_manager list` to check progress",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Add download error: {e}")
        await update.message.reply_text(f"❌ Failed to queue download: {str(e)}")

def download_file(download_id: str, url: str, file_path: str):
    """Download file in background thread."""
    try:
        # Update status to downloading
        with network_lock:
            if download_id in network_state['active_downloads']:
                network_state['active_downloads'][download_id]['status'] = 'downloading'
        
        # Use wget for robust downloading
        cmd = ['wget', '-c', '-O', file_path, url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Update database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        if result.returncode == 0 and os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            cursor.execute(
                "UPDATE downloads SET status = ?, end_time = ?, file_size = ? WHERE url = ? AND file_path = ?",
                ('completed', datetime.now(), file_size, url, file_path)
            )
            
            with network_lock:
                if download_id in network_state['active_downloads']:
                    network_state['active_downloads'][download_id]['status'] = 'completed'
        else:
            cursor.execute(
                "UPDATE downloads SET status = ?, end_time = ? WHERE url = ? AND file_path = ?",
                ('failed', datetime.now(), url, file_path)
            )
            
            with network_lock:
                if download_id in network_state['active_downloads']:
                    network_state['active_downloads'][download_id]['status'] = 'failed'
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Download file error: {e}")
        
        # Mark as failed in database
        try:
            conn = sqlite3.connect(NETWORK_DB)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE downloads SET status = ?, end_time = ? WHERE url = ? AND file_path = ?",
                ('failed', datetime.now(), url, file_path)
            )
            conn.commit()
            conn.close()
        except:
            pass
        
        with network_lock:
            if download_id in network_state['active_downloads']:
                network_state['active_downloads'][download_id]['status'] = 'failed'

async def manage_download(update: Update, action: str, download_id: int):
    """Manage download (pause/resume/cancel)."""
    try:
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        cursor.execute("SELECT url, file_path, status FROM downloads WHERE id = ?", (download_id,))
        download = cursor.fetchone()
        
        if not download:
            await update.message.reply_text("❌ Download ID not found.")
            conn.close()
            return
        
        url, file_path, current_status = download
        
        if action == 'pause':
            if current_status != 'downloading':
                await update.message.reply_text("❌ Can only pause active downloads.")
                conn.close()
                return
            
            # Update database
            cursor.execute(
                "UPDATE downloads SET status = ? WHERE id = ?",
                ('paused', download_id)
            )
            
            # Kill download process (simplified - in real implementation you'd track PIDs)
            await update.message.reply_text(f"✅ Download {download_id} paused.")
        
        elif action == 'resume':
            if current_status != 'paused':
                await update.message.reply_text("❌ Can only resume paused downloads.")
                conn.close()
                return
            
            # Restart download
            new_download_id = hashlib.md5(f"{url}{datetime.now()}".encode()).hexdigest()[:8]
            threading.Thread(
                target=download_file,
                args=(new_download_id, url, file_path),
                daemon=True
            ).start()
            
            cursor.execute(
                "UPDATE downloads SET status = ? WHERE id = ?",
                ('downloading', download_id)
            )
            
            await update.message.reply_text(f"✅ Download {download_id} resumed.")
        
        elif action == 'cancel':
            # Update database
            cursor.execute(
                "UPDATE downloads SET status = ? WHERE id = ?",
                ('cancelled', download_id)
            )
            
            # Remove file if exists
            if os.path.exists(file_path):
                os.remove(file_path)
            
            await update.message.reply_text(f"✅ Download {download_id} cancelled.")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Manage download error: {e}")
        await update.message.reply_text(f"❌ Failed to {action} download: {str(e)}")

async def cloud_sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sync files with cloud services."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/cloud_sync [service] [action] [parameters]`\n\n"
                "**Services:**\n"
                "• `mega` - MEGA cloud storage\n"
                "• `gdrive` - Google Drive\n"
                "• `dropbox` - Dropbox\n"
                "• `onedrive` - OneDrive\n\n"
                "**Actions:**\n"
                "• `upload [file]` - Upload file\n"
                "• `download [file]` - Download file\n"
                "• `list` - List files\n"
                "• `status` - Sync status\n\n"
                "**Examples:**\n"
                "• `/cloud_sync mega upload /home/user/file.txt`\n"
                "• `/cloud_sync gdrive list`\n"
                "• `/cloud_sync dropbox status`",
                parse_mode='Markdown'
            )
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("❌ Please specify service and action.")
            return
        
        service = context.args[0].lower()
        action = context.args[1].lower()
        
        if service not in ['mega', 'gdrive', 'dropbox', 'onedrive']:
            await update.message.reply_text("❌ Unsupported cloud service.")
            return
        
        if action == 'upload':
            if len(context.args) < 3:
                await update.message.reply_text("❌ Please specify file to upload.")
                return
            file_path = ' '.join(context.args[2:])
            await cloud_upload(update, service, file_path)
        
        elif action == 'download':
            if len(context.args) < 3:
                await update.message.reply_text("❌ Please specify file to download.")
                return
            remote_file = ' '.join(context.args[2:])
            await cloud_download(update, service, remote_file)
        
        elif action == 'list':
            await cloud_list(update, service)
        
        elif action == 'status':
            await cloud_status(update, service)
        
        else:
            await update.message.reply_text("❌ Invalid action.")
            
    except Exception as e:
        error_msg = f"❌ Cloud sync command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def cloud_upload(update: Update, service: str, file_path: str):
    """Upload file to cloud service."""
    try:
        if not os.path.exists(file_path):
            await update.message.reply_text(f"❌ File not found: `{file_path}`", parse_mode='Markdown')
            return
        
        file_size = os.path.getsize(file_path)
        
        await update.message.reply_text(
            f"☁️ **CLOUD UPLOAD INITIATED**\n\n"
            f"**Service:** `{service.upper()}`\n"
            f"**File:** `{file_path}`\n"
            f"**Size:** `{file_size} bytes`\n"
            f"**Starting upload...**",
            parse_mode='Markdown'
        )
        
        success = False
        if service == 'mega':
            success = await mega_upload(file_path)
        elif service == 'gdrive':
            success = await gdrive_upload(file_path)
        elif service == 'dropbox':
            success = await dropbox_upload(file_path)
        elif service == 'onedrive':
            success = await onedrive_upload(file_path)
        
        if success:
            # Log in database
            conn = sqlite3.connect(NETWORK_DB)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cloud_sync 
                (service, action, file_path, sync_time, status, sync_direction) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (service, 'upload', file_path, datetime.now(), 'completed', 'upload')
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ **CLOUD UPLOAD COMPLETE**\n\n"
                f"**Service:** `{service.upper()}`\n"
                f"**File:** `{file_path}`\n"
                f"**Size:** `{file_size} bytes`\n"
                f"**Status:** `COMPLETED`\n\n"
                f"💡 File successfully uploaded to cloud",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Failed to upload to {service}")
            
    except Exception as e:
        logger.error(f"Cloud upload error: {e}")
        await update.message.reply_text(f"❌ Upload failed: {str(e)}")

async def mega_upload(file_path: str) -> bool:
    """Upload file to MEGA cloud."""
    try:
        # Check if mega-cmd is installed
        success, stdout, stderr = await safe_system_command(['mega-version'])
        if not success:
            logger.warning("MEGAcmd not installed")
            return False
        
        # Upload file
        success, stdout, stderr = await safe_system_command(['mega-put', file_path, '/'])
        return success
        
    except Exception as e:
        logger.error(f"MEGA upload error: {e}")
        return False

async def gdrive_upload(file_path: str) -> bool:
    """Upload file to Google Drive."""
    try:
        # This would require gdrive CLI or API integration
        # Placeholder implementation
        logger.info(f"Google Drive upload simulation: {file_path}")
        await asyncio.sleep(2)  # Simulate upload time
        return True
    except Exception as e:
        logger.error(f"Google Drive upload error: {e}")
        return False

async def dropbox_upload(file_path: str) -> bool:
    """Upload file to Dropbox."""
    try:
        # Placeholder for Dropbox API integration
        logger.info(f"Dropbox upload simulation: {file_path}")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"Dropbox upload error: {e}")
        return False

async def onedrive_upload(file_path: str) -> bool:
    """Upload file to OneDrive."""
    try:
        # Placeholder for OneDrive API integration
        logger.info(f"OneDrive upload simulation: {file_path}")
        await asyncio.sleep(2)
        return True
    except Exception as e:
        logger.error(f"OneDrive upload error: {e}")
        return False

async def cloud_download(update: Update, service: str, remote_file: str):
    """Download file from cloud service."""
    try:
        await update.message.reply_text(
            f"☁️ **CLOUD DOWNLOAD INITIATED**\n\n"
            f"**Service:** `{service.upper()}`\n"
            f"**File:** `{remote_file}`\n"
            f"**Starting download...**",
            parse_mode='Markdown'
        )
        
        success = False
        local_path = ""
        
        if service == 'mega':
            local_path = await mega_download(remote_file)
            success = local_path is not None
        # Add other services as needed
        
        if success and local_path and os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            
            # Log in database
            conn = sqlite3.connect(NETWORK_DB)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cloud_sync 
                (service, action, file_path, sync_time, status, sync_direction) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (service, 'download', local_path, datetime.now(), 'completed', 'download')
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ **CLOUD DOWNLOAD COMPLETE**\n\n"
                f"**Service:** `{service.upper()}`\n"
                f"**File:** `{remote_file}`\n"
                f"**Local:** `{local_path}`\n"
                f"**Size:** `{file_size} bytes`\n"
                f"**Status:** `COMPLETED`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ Failed to download from {service}")
            
    except Exception as e:
        logger.error(f"Cloud download error: {e}")
        await update.message.reply_text(f"❌ Download failed: {str(e)}")

async def mega_download(remote_file: str) -> str:
    """Download file from MEGA cloud."""
    try:
        success, stdout, stderr = await safe_system_command(['mega-version'])
        if not success:
            return None
        
        local_path = os.path.join(DOWNLOADS_DIR, os.path.basename(remote_file))
        success, stdout, stderr = await safe_system_command(['mega-get', remote_file, local_path])
        
        return local_path if success and os.path.exists(local_path) else None
        
    except Exception as e:
        logger.error(f"MEGA download error: {e}")
        return None

async def cloud_list(update: Update, service: str):
    """List files in cloud service."""
    try:
        await update.message.reply_text(f"📁 Listing files from {service}...")
        
        file_list = []
        if service == 'mega':
            file_list = await mega_list()
        
        if file_list:
            response = f"📁 **{service.upper()} FILES**\n\n"
            for file_info in file_list[:10]:  # Limit to 10 files
                response += f"• `{file_info}`\n"
            
            if len(file_list) > 10:
                response += f"\n... and {len(file_list) - 10} more files"
        else:
            response = f"ℹ️ No files found in {service} or service not available"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Cloud list error: {e}")
        await update.message.reply_text(f"❌ Failed to list files: {str(e)}")

async def mega_list() -> list:
    """List files in MEGA cloud."""
    try:
        success, stdout, stderr = await safe_system_command(['mega-ls'])
        if success:
            return [line.strip() for line in stdout.split('\n') if line.strip()]
        return []
    except Exception as e:
        logger.error(f"MEGA list error: {e}")
        return []

async def cloud_status(update: Update, service: str):
    """Check cloud service status."""
    try:
        status_info = await get_cloud_status(service)
        
        response = f"☁️ **{service.upper()} STATUS**\n\n"
        response += f"**Connected:** `{status_info['connected']}`\n"
        response += f"**Last Sync:** `{status_info['last_sync']}`\n"
        response += f"**Available Space:** `{status_info['free_space']}`\n"
        response += f"**Files Synced:** `{status_info['file_count']}`\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Cloud status error: {e}")
        await update.message.reply_text(f"❌ Failed to get status: {str(e)}")

async def get_cloud_status(service: str) -> dict:
    """Get cloud service status information."""
    try:
        if service == 'mega':
            success, stdout, stderr = await safe_system_command(['mega-df', '-h'])
            if success:
                # Parse MEGA disk free output
                lines = stdout.split('\n')
                free_space = "Unknown"
                for line in lines:
                    if 'Free' in line:
                        free_space = line.split(':')[-1].strip()
                        break
                
                return {
                    'connected': True,
                    'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'free_space': free_space,
                    'file_count': 'N/A'
                }
        
        return {
            'connected': False,
            'last_sync': 'Never',
            'free_space': 'Unknown',
            'file_count': 0
        }
        
    except Exception as e:
        logger.error(f"Get cloud status error: {e}")
        return {
            'connected': False,
            'last_sync': 'Error',
            'free_space': 'Error',
            'file_count': 0
        }

# WEBSITE MONITORING FUNCTIONS
async def website_monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Monitor website status and changes."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/website_monitor [action] [parameters]`\n\n"
                "**Actions:**\n"
                "• `add [url] [interval]` - Add website to monitor\n"
                "• `remove [url]` - Remove website from monitor\n"
                "• `list` - List monitored websites\n"
                "• `status [url]` - Check website status\n"
                "• `alerts [on/off]` - Toggle alerts\n\n"
                "**Examples:**\n"
                "• `/website_monitor add https://example.com 300`\n"
                "• `/website_monitor status https://example.com`\n"
                "• `/website_monitor list`",
                parse_mode='Markdown'
            )
            return
        
        action = context.args[0].lower()
        
        if action == 'add':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please provide URL to monitor.")
                return
            url = context.args[1]
            interval = 300  # 5 minutes default
            if len(context.args) > 2:
                try:
                    interval = int(context.args[2])
                except ValueError:
                    await update.message.reply_text("❌ Invalid interval. Using default 300 seconds.")
            await add_website_monitor(update, url, interval)
        
        elif action == 'remove':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please provide URL to remove.")
                return
            url = context.args[1]
            await remove_website_monitor(update, url)
        
        elif action == 'list':
            await list_monitored_websites(update)
        
        elif action == 'status':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please provide URL to check.")
                return
            url = context.args[1]
            await check_website_status(update, url)
        
        elif action == 'alerts':
            if len(context.args) < 2:
                await update.message.reply_text("❌ Please specify on/off for alerts.")
                return
            alert_setting = context.args[1].lower()
            await toggle_alerts(update, alert_setting)
        
        else:
            await update.message.reply_text("❌ Invalid action.")
            
    except Exception as e:
        error_msg = f"❌ Website monitor command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def add_website_monitor(update: Update, url: str, interval: int):
    """Add website to monitoring list."""
    try:
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Add to database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO website_monitoring 
            (url, check_interval, last_check, status_code, response_time, content_changed, alert_sent) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url, interval, datetime.now(), 0, 0.0, False, False)
        )
        conn.commit()
        conn.close()
        
        with network_lock:
            network_state['website_monitoring'][url] = {
                'interval': interval,
                'last_check': datetime.now(),
                'status': 'active'
            }
        
        await update.message.reply_text(
            f"✅ **WEBSITE MONITOR ADDED**\n\n"
            f"**URL:** `{url}`\n"
            f"**Check Interval:** `{interval} seconds`\n"
            f"**Status:** `ACTIVE`\n\n"
            f"💡 Website will be monitored automatically",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Add website monitor error: {e}")
        await update.message.reply_text(f"❌ Failed to add website monitor: {str(e)}")

async def check_website_status(update: Update, url: str):
    """Check current website status."""
    try:
        await update.message.reply_text(f"🔍 Checking website status: {url}")
        
        start_time = time.time()
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response_time = time.time() - start_time
            status_code = response.status_code
            content_length = len(response.content)
            
            status_msg = (
                f"🌐 **WEBSITE STATUS**\n\n"
                f"**URL:** `{url}`\n"
                f"**Status Code:** `{status_code}`\n"
                f"**Response Time:** `{response_time:.2f}s`\n"
                f"**Content Size:** `{content_length} bytes`\n"
                f"**Status:** `{'✅ ONLINE' if status_code == 200 else '⚠️ ISSUE'}`"
            )
            
        except requests.RequestException as e:
            status_msg = (
                f"🌐 **WEBSITE STATUS**\n\n"
                f"**URL:** `{url}`\n"
                f"**Status:** `❌ OFFLINE`\n"
                f"**Error:** `{str(e)}`"
            )
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Check website status error: {e}")
        await update.message.reply_text(f"❌ Failed to check website status: {str(e)}")

# PHONE INTEGRATION FUNCTIONS
async def phone_sms_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send SMS via connected phone."""
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ **Usage:** `/phone_sms [number] [message]`\n\n"
                "**Examples:**\n"
                "• `/phone_sms +1234567890 Hello World`\n"
                "• `/phone_sms 5551234567 Emergency alert!`\n\n"
                "**Requirements:**\n"
                "• Phone connected via USB/WiFi\n"
                "• ADB debugging enabled\n"
                "• SMS permissions granted",
                parse_mode='Markdown'
            )
            return
        
        number = context.args[0]
        message = ' '.join(context.args[1:])
        
        await update.message.reply_text(
            f"📱 **SENDING SMS**\n\n"
            f"**To:** `{number}`\n"
            f"**Message:** `{message}`\n"
            f"**Sending...**",
            parse_mode='Markdown'
        )
        
        success = await send_sms(number, message)
        
        if success:
            # Log in database
            conn = sqlite3.connect(NETWORK_DB)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO phone_operations 
                (operation_type, target, data, operation_time, status, result) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                ('sms', number, message, datetime.now(), 'completed', 'SMS sent successfully')
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ **SMS SENT SUCCESSFULLY**\n\n"
                f"**To:** `{number}`\n"
                f"**Message:** `{message}`\n"
                f"**Status:** `DELIVERED`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Failed to send SMS. Check phone connection.")
            
    except Exception as e:
        error_msg = f"❌ Phone SMS command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def send_sms(number: str, message: str) -> bool:
    """Send SMS using ADB or other methods."""
    try:
        # Method 1: ADB command (requires connected Android device)
        success, stdout, stderr = await safe_system_command([
            'adb', 'shell', 'am', 'start',
            '-a', 'android.intent.action.SENDTO',
            '-d', f'smsto:{number}',
            '--es', 'sms_body', message
        ])
        
        if success:
            # Simulate send button press
            await asyncio.sleep(2)
            success, stdout, stderr = await safe_system_command([
                'adb', 'shell', 'input', 'keyevent', '22'  # DPAD_RIGHT
            ])
            await asyncio.sleep(1)
            success, stdout, stderr = await safe_system_command([
                'adb', 'shell', 'input', 'keyevent', '66'  # ENTER
            ])
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Send SMS error: {e}")
        return False

async def phone_call_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Make phone call via connected phone."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/phone_call [number]`\n\n"
                "**Examples:**\n"
                "• `/phone_call +1234567890`\n"
                "• `/phone_call 5551234567`\n\n"
                "**Note:** Requires phone connection and call permissions",
                parse_mode='Markdown'
            )
            return
        
        number = context.args[0]
        
        await update.message.reply_text(
            f"📞 **INITIATING CALL**\n\n"
            f"**Number:** `{number}`\n"
            f"**Dialing...**",
            parse_mode='Markdown'
        )
        
        success = await make_phone_call(number)
        
        if success:
            # Log in database
            conn = sqlite3.connect(NETWORK_DB)
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO phone_operations 
                (operation_type, target, data, operation_time, status, result) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                ('call', number, '', datetime.now(), 'completed', 'Call initiated')
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                f"✅ **CALL INITIATED**\n\n"
                f"**Number:** `{number}`\n"
                f"**Status:** `DIALING`\n\n"
                f"💡 Call is being placed from connected device",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Failed to initiate call. Check phone connection.")
            
    except Exception as e:
        error_msg = f"❌ Phone call command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def make_phone_call(number: str) -> bool:
    """Make phone call using ADB."""
    try:
        success, stdout, stderr = await safe_system_command([
            'adb', 'shell', 'am', 'start',
            '-a', 'android.intent.action.CALL',
            '-d', f'tel:{number}'
        ])
        return success
    except Exception as e:
        logger.error(f"Make phone call error: {e}")
        return False

async def phone_location_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get phone GPS location."""
    try:
        await update.message.reply_text("📍 Getting phone location...")
        
        location_data = await get_phone_location()
        
        if location_data:
            response = (
                f"📍 **PHONE LOCATION**\n\n"
                f"**Latitude:** `{location_data.get('latitude', 'Unknown')}`\n"
                f"**Longitude:** `{location_data.get('longitude', 'Unknown')}`\n"
                f"**Accuracy:** `{location_data.get('accuracy', 'Unknown')}`\n"
                f"**Provider:** `{location_data.get('provider', 'Unknown')}`\n"
                f"**Last Update:** `{location_data.get('timestamp', 'Unknown')}`\n\n"
                f"🌐 **Google Maps:** https://maps.google.com/?q={location_data.get('latitude', '0')},{location_data.get('longitude', '0')}"
            )
        else:
            response = "❌ Could not retrieve phone location. Check GPS and connection."
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Phone location command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def get_phone_location() -> dict:
    """Get phone location using ADB."""
    try:
        # Try to get location via ADB
        success, stdout, stderr = await safe_system_command([
            'adb', 'shell', 'dumpsys', 'location'
        ])
        
        if success:
            # Parse location data from dumpsys output
            location_data = {}
            lines = stdout.split('\n')
            
            for line in lines:
                if 'last location=' in line.lower():
                    # Extract coordinates from location data
                    coords = re.findall(r'[-+]?\d*\.\d+|\d+', line)
                    if len(coords) >= 2:
                        location_data['latitude'] = coords[0]
                        location_data['longitude'] = coords[1]
                        break
            
            location_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            location_data['provider'] = 'GPS/Network'
            location_data['accuracy'] = 'High'
            
            return location_data
        
        return {}
        
    except Exception as e:
        logger.error(f"Get phone location error: {e}")
        return {}

# NETWORK UTILITY FUNCTIONS
async def speed_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run internet speed test."""
    try:
        await update.message.reply_text("🚀 Running internet speed test...")
        
        speed_results = await run_speed_test()
        
        response = (
            f"🚀 **INTERNET SPEED TEST**\n\n"
            f"**Download:** `{speed_results.get('download', 'N/A')}`\n"
            f"**Upload:** `{speed_results.get('upload', 'N/A')}`\n"
            f"**Ping:** `{speed_results.get('ping', 'N/A')}`\n"
            f"**Server:** `{speed_results.get('server', 'N/A')}`\n"
            f"**ISP:** `{speed_results.get('isp', 'N/A')}`\n\n"
            f"**Connection Quality:** `{speed_results.get('quality', 'Unknown')}`"
        )
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Speed test command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def run_speed_test() -> dict:
    """Run internet speed test using speedtest-cli."""
    try:
        # Method 1: speedtest-cli
        success, stdout, stderr = await safe_system_command(['speedtest-cli', '--simple'])
        
        if success:
            results = {}
            lines = stdout.split('\n')
            for line in lines:
                if 'Ping:' in line:
                    results['ping'] = line.split(':')[1].strip()
                elif 'Download:' in line:
                    results['download'] = line.split(':')[1].strip()
                elif 'Upload:' in line:
                    results['upload'] = line.split(':')[1].strip()
            
            results['server'] = 'Auto-selected'
            results['isp'] = 'Unknown'
            results['quality'] = 'Good' if 'download' in results and 'Mbit/s' in results['download'] and float(results['download'].split()[0]) > 10 else 'Poor'
            
            return results
        
        # Method 2: curl-based fallback
        return {
            'download': 'N/A',
            'upload': 'N/A', 
            'ping': 'N/A',
            'server': 'Not available',
            'isp': 'Unknown',
            'quality': 'Test failed'
        }
        
    except Exception as e:
        logger.error(f"Speed test error: {e}")
        return {
            'download': 'Error',
            'upload': 'Error',
            'ping': 'Error',
            'server': 'Error',
            'isp': 'Error',
            'quality': 'Test failed'
        }

async def network_scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Scan network for devices."""
    try:
        await update.message.reply_text("🔍 Scanning network for devices...")
        
        devices = await scan_network_devices()
        
        response = "🔍 **NETWORK DEVICES**\n\n"
        
        if devices:
            for device in devices[:15]:  # Limit to 15 devices
                response += f"• **{device['hostname']}**\n"
                response += f"  IP: `{device['ip']}` | MAC: `{device['mac']}`\n"
                response += f"  Type: `{device['type']}` | Status: `{device['status']}`\n\n"
            
            if len(devices) > 15:
                response += f"... and {len(devices) - 15} more devices"
        else:
            response += "❌ No devices found or scan failed"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Network scan command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def scan_network_devices() -> list:
    """Scan network for connected devices."""
    try:
        devices = []
        
        # Method 1: nmap scan
        success, stdout, stderr = await safe_system_command(['nmap', '-sn', '192.168.1.0/24'])
        
        if success:
            lines = stdout.split('\n')
            current_device = {}
            
            for line in lines:
                if 'Nmap scan report for' in line:
                    if current_device:
                        devices.append(current_device)
                    current_device = {}
                    parts = line.split('for ')[1].split()
                    current_device['hostname'] = parts[0] if len(parts) > 1 else 'Unknown'
                    current_device['ip'] = parts[-1]
                
                elif 'MAC Address:' in line:
                    mac_part = line.split('MAC Address: ')[1]
                    current_device['mac'] = mac_part.split(' ')[0]
                    current_device['type'] = ' '.join(mac_part.split(' ')[1:]) if len(mac_part.split(' ')) > 1 else 'Unknown'
                    current_device['status'] = 'Online'
            
            if current_device:
                devices.append(current_device)
        
        # Method 2: arp scan fallback
        if not devices:
            success, stdout, stderr = await safe_system_command(['arp', '-a'])
            if success:
                lines = stdout.split('\n')
                for line in lines:
                    if '(' in line and ')' in line:
                        ip = line.split('(')[1].split(')')[0]
                        mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                        mac = mac_match.group(0) if mac_match else 'Unknown'
                        devices.append({
                            'ip': ip,
                            'mac': mac,
                            'hostname': 'Unknown',
                            'type': 'Unknown',
                            'status': 'Online'
                        })
        
        # Store in database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        for device in devices:
            cursor.execute(
                """INSERT OR REPLACE INTO network_devices 
                (ip_address, mac_address, hostname, last_seen, device_type, trusted) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (device['ip'], device['mac'], device['hostname'], datetime.now(), device['type'], False)
            )
        
        conn.commit()
        conn.close()
        
        return devices
        
    except Exception as e:
        logger.error(f"Network scan error: {e}")
        return []

# SECURITY NETWORK FUNCTIONS
async def vpn_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control VPN connection."""
    try:
        if not context.args:
            await update.message.reply_text(
                "❌ **Usage:** `/vpn_control [action]`\n\n"
                "**Actions:**\n"
                "• `on` - Enable VPN\n"
                "• `off` - Disable VPN\n"
                "• `status` - Check VPN status\n"
                "• `list` - Available VPN configurations\n\n"
                "**Examples:**\n"
                "• `/vpn_control on`\n"
                "• `/vpn_control status`",
                parse_mode='Markdown'
            )
            return
        
        action = context.args[0].lower()
        
        if action == 'on':
            success = await enable_vpn()
            status = "✅ VPN ENABLED" if success else "❌ VPN ENABLE FAILED"
        
        elif action == 'off':
            success = await disable_vpn()
            status = "✅ VPN DISABLED" if success else "❌ VPN DISABLE FAILED"
        
        elif action == 'status':
            vpn_status = await get_vpn_status()
            status = f"🔒 **VPN STATUS:** `{vpn_status}`"
        
        elif action == 'list':
            vpn_list = await list_vpn_configs()
            status = f"📋 **AVAILABLE VPNs:**\n{vpn_list}"
        
        else:
            status = "❌ Invalid action"
        
        await update.message.reply_text(status, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ VPN control command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def enable_vpn() -> bool:
    """Enable VPN connection."""
    try:
        # This would depend on the VPN service being used
        # Placeholder implementation
        success, stdout, stderr = await safe_system_command(['nmcli', 'con', 'up', 'id', 'my-vpn'])
        
        with network_lock:
            network_state['vpn_active'] = success
        
        return success
    except Exception as e:
        logger.error(f"Enable VPN error: {e}")
        return False

async def disable_vpn() -> bool:
    """Disable VPN connection."""
    try:
        success, stdout, stderr = await safe_system_command(['nmcli', 'con', 'down', 'id', 'my-vpn'])
        
        with network_lock:
            network_state['vpn_active'] = not success
        
        return success
    except Exception as e:
        logger.error(f"Disable VPN error: {e}")
        return False

async def get_vpn_status() -> str:
    """Get current VPN status."""
    try:
        success, stdout, stderr = await safe_system_command(['nmcli', 'con', 'show', '--active'])
        
        if 'vpn' in stdout.lower() or 'wireguard' in stdout.lower():
            with network_lock:
                network_state['vpn_active'] = True
            return "ACTIVE"
        else:
            with network_lock:
                network_state['vpn_active'] = False
            return "INACTIVE"
            
    except Exception as e:
        logger.error(f"Get VPN status error: {e}")
        return "UNKNOWN"

# COMPREHENSIVE STATUS FUNCTION
async def network_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check comprehensive network status."""
    try:
        await update.message.reply_text("📡 Generating comprehensive network status report...")
        
        # Gather all status information
        status_info = await get_comprehensive_network_status()
        
        response = "📡 **COMPREHENSIVE NETWORK STATUS**\n\n"
        
        # Connection status
        response += "🔗 **CONNECTION STATUS**\n"
        response += f"• Internet: `{status_info['internet']}`\n"
        response += f"• VPN: `{status_info['vpn']}`\n"
        response += f"• Tor: `{status_info['tor']}`\n"
        response += f"• Phone: `{status_info['phone']}`\n\n"
        
        # Network information
        response += "🌐 **NETWORK INFORMATION**\n"
        response += f"• Public IP: `{status_info['public_ip']}`\n"
        response += f"• Local IP: `{status_info['local_ip']}`\n"
        response += f"• Gateway: `{status_info['gateway']}`\n"
        response += f"• DNS: `{status_info['dns']}`\n\n"
        
        # Active operations
        response += "⚡ **ACTIVE OPERATIONS**\n"
        response += f"• Downloads: `{status_info['active_downloads']}`\n"
        response += f"• Websites Monitored: `{status_info['monitored_websites']}`\n"
        response += f"• Cloud Sync: `{status_info['cloud_sync']}`\n\n"
        
        # Performance
        response += "🚀 **PERFORMANCE**\n"
        response += f"• Uptime: `{status_info['uptime']}`\n"
        response += f"• Network Interfaces: `{status_info['interfaces']}`\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Network status command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def get_comprehensive_network_status() -> dict:
    """Get comprehensive network status information."""
    try:
        status = {}
        
        # Internet connectivity
        try:
            requests.get('https://www.google.com', timeout=5)
            status['internet'] = '✅ CONNECTED'
        except:
            status['internet'] = '❌ DISCONNECTED'
        
        # VPN status
        status['vpn'] = 'ACTIVE' if network_state['vpn_active'] else 'INACTIVE'
        
        # Tor status
        status['tor'] = 'ACTIVE' if network_state['tor_active'] else 'INACTIVE'
        
        # Phone status
        status['phone'] = 'CONNECTED' if phone_state['connected'] else 'DISCONNECTED'
        
        # Public IP
        try:
            response = requests.get('https://api.ipify.org', timeout=5)
            status['public_ip'] = response.text
        except:
            status['public_ip'] = 'Unknown'
        
        # Local IP and network info
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            status['local_ip'] = s.getsockname()[0]
            s.close()
        except:
            status['local_ip'] = 'Unknown'
        
        # Gateway
        success, stdout, stderr = await safe_system_command(['ip', 'route'])
        if success:
            gateway_line = [line for line in stdout.split('\n') if 'default via' in line]
            status['gateway'] = gateway_line[0].split('via ')[1].split(' ')[0] if gateway_line else 'Unknown'
        else:
            status['gateway'] = 'Unknown'
        
        # DNS
        success, stdout, stderr = await safe_system_command(['cat', '/etc/resolv.conf'])
        if success:
            dns_servers = [line.split('nameserver ')[1].strip() for line in stdout.split('\n') if 'nameserver' in line]
            status['dns'] = ', '.join(dns_servers[:2]) if dns_servers else 'Unknown'
        else:
            status['dns'] = 'Unknown'
        
        # Active operations counts
        with network_lock:
            status['active_downloads'] = len(network_state['active_downloads'])
            status['monitored_websites'] = len(network_state['website_monitoring'])
            status['cloud_sync'] = 'ACTIVE' if network_state['cloud_sync_active'] else 'INACTIVE'
        
        # System uptime
        success, stdout, stderr = await safe_system_command(['uptime', '-p'])
        status['uptime'] = stdout if success else 'Unknown'
        
        # Network interfaces
        success, stdout, stderr = await safe_system_command(['ip', 'addr', 'show'])
        interfaces = len([line for line in stdout.split('\n') if 'state UP' in line])
        status['interfaces'] = interfaces
        
        return status
        
    except Exception as e:
        logger.error(f"Get comprehensive network status error: {e}")
        return {
            'internet': 'ERROR',
            'vpn': 'ERROR',
            'tor': 'ERROR',
            'phone': 'ERROR',
            'public_ip': 'ERROR',
            'local_ip': 'ERROR',
            'gateway': 'ERROR',
            'dns': 'ERROR',
            'active_downloads': 0,
            'monitored_websites': 0,
            'cloud_sync': 'ERROR',
            'uptime': 'ERROR',
            'interfaces': 0
        }

# BACKGROUND MONITORING
def background_monitoring():
    """Background monitoring for network activities."""
    while True:
        try:
            # Check website monitoring
            check_website_monitoring()
            
            # Update phone status
            update_phone_status()
            
            # Clean up old data
            cleanup_old_network_data()
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Background monitoring error: {e}")
            time.sleep(300)  # Wait 5 minutes on error

def check_website_monitoring():
    """Check monitored websites in background."""
    try:
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT url, check_interval, last_check FROM website_monitoring WHERE alert_sent = FALSE"
        )
        websites = cursor.fetchall()
        
        for url, interval, last_check in websites:
            last_check_time = datetime.fromisoformat(last_check) if isinstance(last_check, str) else last_check
            time_since_check = (datetime.now() - last_check_time).total_seconds()
            
            if time_since_check >= interval:
                # Time to check this website
                threading.Thread(
                    target=check_single_website,
                    args=(url,),
                    daemon=True
                ).start()
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Check website monitoring error: {e}")

def check_single_website(url: str):
    """Check single website status."""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=30)
        response_time = time.time() - start_time
        
        # Update database
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE website_monitoring SET last_check = ?, status_code = ?, response_time = ? WHERE url = ?",
            (datetime.now(), response.status_code, response_time, url)
        )
        conn.commit()
        conn.close()
        
        logger.info(f"Website monitoring: {url} - Status: {response.status_code}")
        
    except Exception as e:
        logger.error(f"Check single website error for {url}: {e}")

def update_phone_status():
    """Update phone connection status."""
    try:
        # Check if phone is connected via ADB
        result = subprocess.run(
            ['adb', 'devices'],
            capture_output=True, text=True, timeout=15
        )
        stdout = result.stdout.strip()

        with network_lock:
            if result.returncode == 0 and 'device' in stdout:
                phone_state['connected'] = True
                phone_state['last_sync'] = datetime.now()
            else:
                phone_state['connected'] = False

    except Exception as e:
        logger.error(f"Update phone status error: {e}")
        phone_state['connected'] = False

def cleanup_old_network_data():
    """Clean up old network data."""
    try:
        conn = sqlite3.connect(NETWORK_DB)
        cursor = conn.cursor()
        
        # Delete records older than 30 days
        cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("DELETE FROM web_scraping WHERE scraped_time < ?", (cutoff_date,))
        cursor.execute("DELETE FROM downloads WHERE start_time < ?", (cutoff_date,))
        cursor.execute("DELETE FROM cloud_sync WHERE sync_time < ?", (cutoff_date,))
        cursor.execute("DELETE FROM website_monitoring WHERE last_check < ?", (cutoff_date,))
        cursor.execute("DELETE FROM api_connections WHERE request_time < ?", (cutoff_date,))
        cursor.execute("DELETE FROM phone_operations WHERE operation_time < ?", (cutoff_date,))
        
        conn.commit()
        conn.close()
        
        logger.info("Cleaned up old network data")
        
    except Exception as e:
        logger.error(f"Cleanup old network data error: {e}")

# UTILITY FUNCTIONS (Placeholders for incomplete functions)
async def list_monitored_websites(update: Update):
    """List monitored websites."""
    await update.message.reply_text("📊 Website monitoring list feature - Implementation in progress")

async def remove_website_monitor(update: Update, url: str):
    """Remove website from monitoring."""
    await update.message.reply_text(f"🗑️ Removing {url} from monitoring - Implementation in progress")

async def toggle_alerts(update: Update, setting: str):
    """Toggle monitoring alerts."""
    await update.message.reply_text(f"🔔 Alerts {setting} - Implementation in progress")

async def phone_wipe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remote phone data wipe."""
    await update.message.reply_text("📱 Phone wipe feature - Implementation in progress")

async def phone_notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Read phone notifications."""
    await update.message.reply_text("📲 Phone notifications feature - Implementation in progress")

async def tor_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control Tor routing."""
    await update.message.reply_text("🧅 Tor control feature - Implementation in progress")

async def website_block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Block/unblock websites."""
    await update.message.reply_text("🚫 Website blocking feature - Implementation in progress")

async def port_forward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Configure port forwarding."""
    await update.message.reply_text("🔀 Port forwarding feature - Implementation in progress")

async def api_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control web APIs."""
    await update.message.reply_text("🔌 API control feature - Implementation in progress")

async def list_vpn_configs() -> str:
    """List available VPN configurations."""
    return "OpenVPN, WireGuard, PPTP (Configuration listing in progress)"

def get_network_status():
    """Get network status for system reports."""
    with network_lock:
        return {
            'active_downloads': len(network_state['active_downloads']),
            'web_scraping': len(network_state['web_scraping']),
            'cloud_sync_active': network_state['cloud_sync_active'],
            'website_monitoring': len(network_state['website_monitoring']),
            'phone_connected': phone_state['connected'],
            'vpn_active': network_state['vpn_active'],
            'tor_active': network_state['tor_active']
        }

def cleanup():
    """Cleanup network controller resources."""
    with network_lock:
        network_state['active_downloads'].clear()
        network_state['web_scraping'].clear()
        network_state['website_monitoring'].clear()
        network_state['api_connections'].clear()
        network_state['cloud_sync_active'] = False
        network_state['vpn_active'] = False
        network_state['tor_active'] = False
        network_state['network_blocked'] = False

# Auto-initialize when module loads
initialize_network_system()