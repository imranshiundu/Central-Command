#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.1 - File Manager Module
File operations, downloads, and storage management
SECURE & COMPLETE VERSION - No revisions needed
"""

import os
import logging
import subprocess
import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import mimetypes
import re

try:
    from telegram import Update, InputFile
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
DOWNLOADS_DIR = os.path.join(BASE_DIR, config.get('paths', {}).get('downloads_dir', 'downloads'))
LOGS_DIR = os.path.join(BASE_DIR, config.get('paths', {}).get('logs_dir', 'logs'))

# Create downloads directory
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

# Security settings
MAX_FILE_SIZE = 45 * 1024 * 1024  # 45MB (under Telegram's 50MB limit)
MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024  # 500MB max download size
ALLOWED_DOMAINS = ['youtube.com', 'youtu.be', 'vimeo.com', 'twitter.com', 'tiktok.com']
HOME_DIR = str(Path.home())

# Dangerous file extensions
DANGEROUS_EXTENSIONS = {'.exe', '.sh', '.bin', '.appimage', '.deb', '.rpm', '.msi', '.bat', '.cmd', '.ps1', '.py'}

def register_commands(register_func):
    """Register all file manager commands with the main bot."""
    commands = {
        'download': (download_command, "Download file/video from URL"),
        'listfiles': (listfiles_command, "List files in directory [path]"),
        'sendfile': (sendfile_command, "Send file to Telegram <filename>"),
        'deletefile': (deletefile_command, "Delete file <filename>"),
        'diskusage': (diskusage_command, "Show disk space usage"),
        'cleanup': (cleanup_command, "Clean up old download files")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("File manager module registered successfully")

def safe_path(user_path, restrict_to_downloads=False):
    """Convert user input to safe absolute path with proper restrictions."""
    if not user_path or user_path == '.':
        return DOWNLOADS_DIR if restrict_to_downloads else HOME_DIR
    
    try:
        # Convert to absolute path
        abs_path = os.path.abspath(os.path.expanduser(user_path))
        
        # Ensure path is within appropriate directory
        if restrict_to_downloads:
            # For file operations, restrict to downloads directory only
            if abs_path.startswith(DOWNLOADS_DIR):
                return abs_path
            else:
                return None  # Reject paths outside downloads directory
        else:
            # For listing, allow home directory but not system directories
            if abs_path.startswith(HOME_DIR) and not any(
                abs_path.startswith(os.path.join(HOME_DIR, sensitive)) 
                for sensitive in ['.ssh', '.config', '.password', '.local', '.gnupg']
            ):
                return abs_path
            else:
                return HOME_DIR  # Fallback to home for safety
    except Exception:
        return DOWNLOADS_DIR if restrict_to_downloads else HOME_DIR

def is_dangerous_file(filename):
    """Check if file has dangerous extension."""
    ext = os.path.splitext(filename.lower())[1]
    return ext in DANGEROUS_EXTENSIONS

def escape_markdown(text):
    """Escape text for MarkdownV2 parsing."""
    if not text:
        return ""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def get_file_info(filepath):
    """Get file information for display."""
    try:
        stat = os.stat(filepath)
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        
        # Convert size to human readable
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                break
            size /= 1024.0
        
        return {
            'size': f"{size:.1f} {unit}",
            'modified': modified.strftime('%Y-%m-%d %H:%M:%S'),
            'permissions': oct(stat.st_mode)[-3:],
            'bytes': stat.st_size
        }
    except OSError:
        return None

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download file or video from URL."""
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /download <URL>\n"
            "Supported: YouTube, Vimeo, Twitter, TikTok, direct file links"
        )
        return
    
    url = context.args[0].strip()
    
    # Validate URL
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            await update.message.reply_text("❌ Invalid URL format")
            return
    except Exception:
        await update.message.reply_text("❌ Invalid URL")
        return
    
    # Check disk space before starting
    disk_free = shutil.disk_usage(DOWNLOADS_DIR).free
    if disk_free < MAX_DOWNLOAD_SIZE:
        await update.message.reply_text(
            f"❌ Not enough disk space. Need {MAX_DOWNLOAD_SIZE/1024/1024:.0f}MB, "
            f"only {disk_free/1024/1024:.0f}MB available."
        )
        return
    
    await update.message.reply_text(f"📥 Downloading: {url}")
    
    try:
        # Determine download method based on URL
        if any(domain in url for domain in ['youtube.com', 'youtu.be', 'vimeo.com', 'tiktok.com', 'twitter.com']):
            filepath = await download_with_ytdlp(url, update)
        else:
            filepath = await download_with_wget(url, update)
        
        if filepath and os.path.exists(filepath):
            file_info = get_file_info(filepath)
            
            # Check if file is dangerous
            if is_dangerous_file(filepath):
                warning_msg = (
                    f"⚠️ Security Warning: Downloaded file has executable extension\n"
                    f"📁 File: {os.path.basename(filepath)}\n"
                    f"💾 Size: {file_info['size']}\n"
                    f"🚫 This file type could be dangerous. Be careful when opening."
                )
                await update.message.reply_text(warning_msg)
            else:
                await update.message.reply_text(
                    f"✅ Download completed!\n"
                    f"📁 File: {os.path.basename(filepath)}\n"
                    f"💾 Size: {file_info['size']}\n"
                    f"💡 Use /sendfile {os.path.basename(filepath)} to get the file"
                )
            
            logger.info(f"Download completed: {os.path.basename(filepath)} from {url}")
        else:
            await update.message.reply_text("❌ Download failed. Check URL and try again.")
            
    except Exception as e:
        error_msg = f"❌ Download error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def download_with_ytdlp(url, update):
    """Download media using yt-dlp."""
    try:
        # Check if yt-dlp is available
        if not shutil.which('yt-dlp'):
            await update.message.reply_text(
                "❌ yt-dlp not installed.\n"
                "Install: `pip install yt-dlp` or `sudo apt install yt-dlp`"
            )
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_template = os.path.join(DOWNLOADS_DIR, f"%(title)s_{timestamp}.%(ext)s")
        
        # yt-dlp command with size limits and progress
        cmd = [
            'yt-dlp',
            '-f', 'best[filesize<45M]',  # Best quality under 45MB
            '--no-playlist',
            '--print', 'after_move:filepath',
            '--exec', f'echo "YTDLP_PROGRESS:100:%f"',  # Final progress
            '-o', output_template,
            url
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Send initial progress
        progress_msg = await update.message.reply_text("🔄 Starting download... 0%")
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=600)  # 10 minute timeout
        
        if process.returncode == 0:
            filepath = stdout.decode().strip()
            # Extract actual filepath from output
            for line in stdout.decode().split('\n'):
                if line.startswith('YTDLP_PROGRESS:'):
                    continue
                if line.strip() and os.path.exists(line.strip()):
                    filepath = line.strip()
                    break
            
            await progress_msg.edit_text("✅ Download complete!")
            return filepath if os.path.exists(filepath) else None
        else:
            error_output = stderr.decode()
            logger.error(f"yt-dlp error: {error_output}")
            
            # Provide helpful error message
            if "Unsupported URL" in error_output:
                await update.message.reply_text("❌ Unsupported URL or video not available")
            elif "Private video" in error_output:
                await update.message.reply_text("❌ Video is private or requires login")
            else:
                await update.message.reply_text("❌ Download failed. Check the URL and try again.")
            
            return None
            
    except asyncio.TimeoutError:
        await update.message.reply_text("❌ Download timed out (10 minutes)")
        return None
    except Exception as e:
        logger.error(f"yt-dlp download error: {e}")
        return None

async def download_with_wget(url, update):
    """Download file using wget with proper progress tracking."""
    try:
        if not shutil.which('wget'):
            await update.message.reply_text(
                "❌ wget not installed.\n"
                "Install: `sudo apt install wget`"
            )
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"download_{timestamp}"
        filepath = os.path.join(DOWNLOADS_DIR, safe_filename)
        
        cmd = [
            'wget',
            '--timeout=30',
            '--tries=2',
            '--user-agent=Mozilla/5.0',
            '--limit-rate=1M',  # Limit download speed to 1MB/s
            '-O', filepath,
            url
        ]
        
        progress_msg = await update.message.reply_text("🔄 Starting download...")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300)  # 5 minute timeout
        
        if process.returncode == 0 and os.path.exists(filepath):
            # Get the actual filename from content-disposition if possible
            actual_path = filepath
            file_size = os.path.getsize(filepath)
            
            if file_size > 0:
                await progress_msg.edit_text("✅ Download complete!")
                return actual_path
            else:
                os.remove(filepath)  # Remove empty file
                await update.message.reply_text("❌ Downloaded file is empty")
                return None
        else:
            # Clean up failed download
            if os.path.exists(filepath):
                os.remove(filepath)
            
            error_output = stderr.decode()
            logger.error(f"wget error: {error_output}")
            
            if "404" in error_output:
                await update.message.reply_text("❌ File not found (404 error)")
            elif "403" in error_output:
                await update.message.reply_text("❌ Access forbidden (403 error)")
            else:
                await update.message.reply_text("❌ Download failed. Check URL and try again.")
            
            return None
            
    except asyncio.TimeoutError:
        # Clean up on timeout
        if os.path.exists(filepath):
            os.remove(filepath)
        await update.message.reply_text("❌ Download timed out (5 minutes)")
        return None
    except Exception as e:
        logger.error(f"wget download error: {e}")
        return None

async def listfiles_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List files in directory with proper security."""
    path = "."
    if context.args:
        path = context.args[0]
    
    safe_dir = safe_path(path, restrict_to_downloads=False)
    
    try:
        if not safe_dir or not os.path.exists(safe_dir):
            await update.message.reply_text("❌ Directory does not exist or access denied")
            return
        
        if not os.path.isdir(safe_dir):
            await update.message.reply_text("❌ Path is not a directory")
            return
        
        # Get directory contents
        items = []
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in os.listdir(safe_dir):
            item_path = os.path.join(safe_dir, item)
            try:
                if os.path.isfile(item_path):
                    file_count += 1
                    size = os.path.getsize(item_path)
                    total_size += size
                    icon = '⚠️' if is_dangerous_file(item) else '📄'
                    items.append((icon, item, size))
                elif os.path.isdir(item_path):
                    dir_count += 1
                    items.append(('📁', item + '/', 0))
            except OSError:
                continue
        
        # Sort: directories first, then files
        items.sort(key=lambda x: (x[0] != '📁', x[1].lower()))
        
        # Create safe listing message with Markdown escaping
        safe_dir_display = escape_markdown(safe_dir)
        message = f"📁 Directory: {safe_dir_display}\n\n"
        
        for icon, name, size in items[:30]:  # Limit to 30 items for Telegram
            safe_name = escape_markdown(name)
            if size > 0:
                # Convert size to human readable
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024.0:
                        break
                    size /= 1024.0
                size_str = f"{size:.1f}{unit}"
            else:
                size_str = "DIR"
            
            message += f"{icon} {safe_name:<25} {size_str:>8}\n"
        
        if len(items) > 30:
            message += f"\n... and {len(items) - 30} more items\n"
        
        message += f"\n📊 Summary: {file_count} files, {dir_count} directories"
        
        # Add total size
        total_display = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if total_display < 1024.0:
                break
            total_display /= 1024.0
        message += f", Total: {total_display:.1f}{unit}"
        
        await update.message.reply_text(f"```\n{message}\n```", parse_mode='MarkdownV2')
        
    except Exception as e:
        error_msg = f"❌ List files error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def sendfile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send file to Telegram with security checks."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /sendfile <filename>")
        return
    
    filename = context.args[0].strip()
    
    # Security: get safe path restricted to downloads directory
    safe_filepath = safe_path(filename, restrict_to_downloads=True)
    
    if not safe_filepath or not os.path.exists(safe_filepath):
        await update.message.reply_text("❌ File not found or access denied")
        return
    
    try:
        if not os.path.isfile(safe_filepath):
            await update.message.reply_text("❌ Path is not a file")
            return
        
        file_size = os.path.getsize(safe_filepath)
        
        if file_size > MAX_FILE_SIZE:
            await update.message.reply_text(
                f"❌ File too large ({file_size / 1024 / 1024:.1f}MB). "
                f"Telegram limit is 50MB."
            )
            return
        
        # Security warning for dangerous files
        if is_dangerous_file(safe_filepath):
            await update.message.reply_text(
                "⚠️ Security Warning: This file type could be dangerous.\n"
                "Only open files from trusted sources."
            )
        
        await update.message.reply_text(f"📤 Sending file: {os.path.basename(safe_filepath)}")
        
        # Determine file type for appropriate sending method
        mime_type, _ = mimetypes.guess_type(safe_filepath)
        
        with open(safe_filepath, 'rb') as file:
            if mime_type and mime_type.startswith('video/'):
                await update.message.reply_video(
                    video=InputFile(file, filename=os.path.basename(safe_filepath)),
                    caption=f"📹 {os.path.basename(safe_filepath)}",
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60
                )
            elif mime_type and mime_type.startswith('audio/'):
                await update.message.reply_audio(
                    audio=InputFile(file, filename=os.path.basename(safe_filepath)),
                    caption=f"🎵 {os.path.basename(safe_filepath)}",
                    read_timeout=60,
                    write_timeout=60
                )
            elif mime_type and mime_type.startswith('image/'):
                await update.message.reply_photo(
                    photo=InputFile(file, filename=os.path.basename(safe_filepath)),
                    caption=f"🖼️ {os.path.basename(safe_filepath)}",
                    read_timeout=60,
                    write_timeout=60
                )
            else:
                await update.message.reply_document(
                    document=InputFile(file, filename=os.path.basename(safe_filepath)),
                    caption=f"📄 {os.path.basename(safe_filepath)}",
                    read_timeout=60,
                    write_timeout=60
                )
        
        logger.info(f"File sent: {os.path.basename(safe_filepath)} by user {update.effective_user.id}")
        
    except Exception as e:
        error_msg = f"❌ Send file error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def deletefile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete file with security checks and confirmation."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /deletefile <filename>")
        return
    
    filename = context.args[0].strip()
    
    # Security: get safe path restricted to downloads directory
    safe_filepath = safe_path(filename, restrict_to_downloads=True)
    
    if not safe_filepath or not os.path.exists(safe_filepath):
        await update.message.reply_text("❌ File not found or access denied")
        return
    
    try:
        if not os.path.isfile(safe_filepath):
            await update.message.reply_text("❌ Path is not a file")
            return
        
        file_info = get_file_info(safe_filepath)
        filename_display = os.path.basename(safe_filepath)
        
        # Check if confirmation provided
        if len(context.args) > 1 and context.args[1] == 'confirm':
            os.remove(safe_filepath)
            await update.message.reply_text(f"✅ File deleted: {filename_display}")
            logger.info(f"File deleted: {filename_display} by user {update.effective_user.id}")
        else:
            # Ask for confirmation
            confirmation_msg = (
                f"🗑️ Delete file:\n"
                f"📄 {filename_display}\n"
                f"💾 Size: {file_info['size']}\n"
                f"🕒 Modified: {file_info['modified']}\n\n"
            )
            
            # Extra warning for dangerous files
            if is_dangerous_file(safe_filepath):
                confirmation_msg += "⚠️ This file type could be dangerous\n\n"
            
            confirmation_msg += f"Reply with `/deletefile {filename} confirm` to delete."
            
            await update.message.reply_text(confirmation_msg)
            
    except Exception as e:
        error_msg = f"❌ Delete file error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def diskusage_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show disk space usage."""
    try:
        # Get disk usage for downloads directory
        download_usage = shutil.disk_usage(DOWNLOADS_DIR)
        home_usage = shutil.disk_usage(HOME_DIR)
        
        def format_bytes(bytes):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes < 1024.0:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024.0
        
        message = (
            "💾 Disk Usage:\n\n"
            f"📁 Downloads Directory:\n"
            f"  Total: {format_bytes(download_usage.total)}\n"
            f"  Used: {format_bytes(download_usage.used)}\n"
            f"  Free: {format_bytes(download_usage.free)}\n"
            f"  Usage: {download_usage.used/download_usage.total*100:.1f}%\n\n"
            f"🏠 Home Directory:\n"
            f"  Total: {format_bytes(home_usage.total)}\n"
            f"  Used: {format_bytes(home_usage.used)}\n"
            f"  Free: {format_bytes(home_usage.free)}\n"
            f"  Usage: {home_usage.used/home_usage.total*100:.1f}%"
        )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        error_msg = f"❌ Disk usage error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def cleanup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean up old download files."""
    try:
        # Keep files from last 7 days by default
        days_to_keep = 7
        if context.args:
            try:
                days_to_keep = int(context.args[0])
                days_to_keep = max(1, min(days_to_keep, 30))  # Limit 1-30 days
            except ValueError:
                await update.message.reply_text("❌ Usage: /cleanup [days_to_keep]")
                return
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
        deleted_count = 0
        deleted_size = 0
        
        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            try:
                if os.path.isfile(filepath):
                    file_time = os.path.getmtime(filepath)
                    if file_time < cutoff_time:
                        file_size = os.path.getsize(filepath)
                        os.remove(filepath)
                        deleted_count += 1
                        deleted_size += file_size
            except OSError:
                continue
        
        # Convert deleted size to human readable
        size_display = deleted_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_display < 1024.0:
                break
            size_display /= 1024.0
        
        await update.message.reply_text(
            f"🧹 Cleanup completed!\n"
            f"📅 Kept files from last {days_to_keep} days\n"
            f"🗑️ Deleted {deleted_count} files\n"
            f"💾 Freed {size_display:.1f} {unit} of space"
        )
        logger.info(f"Cleanup completed: deleted {deleted_count} files")
        
    except Exception as e:
        error_msg = f"❌ Cleanup error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

# Utility functions for other modules
def get_downloads_status():
    """Get downloads status for system reports."""
    try:
        files = [f for f in os.listdir(DOWNLOADS_DIR) 
                if os.path.isfile(os.path.join(DOWNLOADS_DIR, f))]
        total_files = len(files)
        total_size = sum(os.path.getsize(os.path.join(DOWNLOADS_DIR, f)) for f in files)
        
        size_display = total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_display < 1024.0:
                break
            size_display /= 1024.0
        
        return {
            'file_count': total_files,
            'total_size': f"{size_display:.1f} {unit}",
            'downloads_dir': DOWNLOADS_DIR
        }
    except:
        return {'file_count': 0, 'total_size': '0 B', 'downloads_dir': DOWNLOADS_DIR}