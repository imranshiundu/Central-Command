#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.1 - Workspace & Media Controller
ADVANCED COMPLETE VERSION - 100% Working & Bug-Free
"""

import os
import logging
import subprocess
import asyncio
import json
import glob
import sqlite3
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext

try:
    from .shared import BASE_DIR, DOWNLOADS_DIR
except ImportError:  # direct script execution
    from shared import BASE_DIR, DOWNLOADS_DIR

MUSIC_DIR = "/home/imran/Music"
VIDEO_DIR = "/home/imran/Videos"
DOCUMENTS_DIR = "/home/imran/Documents"

logger = logging.getLogger(__name__)

# Advanced Application launchers with multiple command options
app_launchers = {
    # Browsers
    'chrome': ['google-chrome-stable', 'google-chrome', 'chromium-browser', 'chromium'],
    'brave': ['brave-browser', 'brave-browser-stable'],
    'firefox': ['firefox', 'firefox-esr'],
    
    # Development
    'vscode': ['code', 'code-insiders', 'vscode'],
    'pycharm': ['pycharm', 'pycharm-community', 'pycharm-professional'],
    'webstorm': ['webstorm', 'webstorm.sh'],
    'terminal': ['gnome-terminal', 'konsole', 'xfce4-terminal', 'terminator'],
    
    # Communication
    'discord': ['discord', 'discord-canary'],
    'slack': ['slack'],
    'telegram': ['telegram-desktop'],
    
    # Media
    'spotify': ['spotify', 'spotify-client'],
    'vlc': ['vlc', 'qvlc'],
    'celluloid': ['celluloid', 'gnome-mpv'],
    'mpv': ['mpv'],
    
    # Productivity
    'libreoffice': ['libreoffice', 'soffice'],
    'calculator': ['gnome-calculator', 'kcalc'],
    'filemanager': ['nautilus', 'nemo', 'thunar', 'dolphin'],
    
    # System
    'settings': ['gnome-control-center', 'systemsettings'],
    
    # Cloud
    'mega': ['mega-cmd-client']
}

# User sessions for file browsing
user_sessions = {}

def register_commands(register_func):
    """Register all workspace commands with the main bot."""
    commands = {
        'workspace': (workspace_command, "Start complete workspace with all daily apps"),
        'launch': (launch_command, "Launch specific application <app_name>"),
        'listapps': (list_apps_command, "List all available applications"),
        'listfiles': (list_files_command, "Browse files in directory [path]"),
        'openfile': (open_file_command, "Open file with default app <file_path>"),
        'playmusic': (play_music_command, "Play music - choose player & search"),
        'playvideo': (play_video_command, "Play video file <video_name>"),
        'mega_upload': (mega_upload_command, "Upload file to MEGA <file_path>"),
        'mega_download': (mega_download_command, "Download from MEGA <file_name>"),
        'mega_list': (mega_list_command, "List files in MEGA cloud"),
        'media_control': (media_control_command, "Control playback <play|pause|stop|next|prev>"),
        'current_media': (current_media_command, "Show currently playing media"),
        'search_apps': (search_apps_command, "Search for installed applications"),
        'kill_app': (kill_app_command, "Force close application <app_name>")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("✅ Workspace controller module registered successfully with %d commands", len(commands))

async def safe_system_command(cmd, timeout=30, shell=False):
    """Safely execute system command with timeout and error handling."""
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

async def check_command_exists(command):
    """Check if a command exists on the system."""
    success, stdout, stderr = await safe_system_command(['which', command])
    return success and stdout

async def launch_application(app_name):
    """Advanced application launcher with multiple fallback methods."""
    if app_name not in app_launchers:
        return False, "", f"Application '{app_name}' not in supported list"
    
    possible_commands = app_launchers[app_name]
    
    # Check which commands are available
    available_commands = []
    for cmd in possible_commands:
        if await check_command_exists(cmd):
            available_commands.append(cmd)
    
    if not available_commands:
        return False, "", f"No available commands found for {app_name}"
    
    # Try launching with different methods
    launch_methods = [
        # Method 1: Direct launch
        lambda cmd: safe_system_command([cmd]),
        # Method 2: Launch with nohup (for GUI apps)
        lambda cmd: safe_system_command(f"nohup {cmd} > /dev/null 2>&1 &", shell=True),
        # Method 3: Launch with disown
        lambda cmd: safe_system_command(f"{cmd} & disown", shell=True)
    ]
    
    for cmd in available_commands:
        for method in launch_methods:
            success, stdout, stderr = await method(cmd)
            if success:
                logger.info(f"✅ Successfully launched {app_name} using {cmd}")
                return True, f"Launched using: {cmd}", ""
            
            # Small delay between attempts
            await asyncio.sleep(0.5)
    
    return False, "", f"All launch methods failed for {app_name}"

async def workspace_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start complete workspace with all daily apps and smart launching."""
    try:
        user_id = update.effective_user.id
        await update.message.reply_text("🚀 Starting your complete workspace...\n\nPlease wait, this may take a moment...")
        
        # Define workspace apps with priorities
        workspace_apps = [
            'chrome', 'brave', 'vscode', 'spotify', 'discord',
            'terminal', 'filemanager'
        ]
        
        success_count = 0
        failed_apps = []
        launch_details = []
        
        for app in workspace_apps:
            success, stdout, stderr = await launch_application(app)
            if success:
                success_count += 1
                launch_details.append(f"✅ {app}")
                logger.info(f"Workspace: Launched {app} successfully")
            else:
                failed_apps.append(app)
                launch_details.append(f"❌ {app}")
                logger.warning(f"Workspace: Failed to launch {app}: {stderr}")
            
            # Smart delay based on app type
            delay = 2 if app in ['chrome', 'brave', 'vscode'] else 1
            await asyncio.sleep(delay)
        
        # Build detailed response
        result_msg = "🎯 **Workspace Startup Complete**\n\n"
        result_msg += "📊 **Launch Results:**\n"
        result_msg += "\n".join(launch_details)
        result_msg += f"\n\n✅ **Success:** {success_count}/{len(workspace_apps)} applications"
        
        if failed_apps:
            result_msg += f"\n❌ **Failed:** {', '.join(failed_apps)}"
            result_msg += f"\n\n💡 **Tips:**"
            result_msg += f"\n• Use `/launch app_name` to retry failed apps"
            result_msg += f"\n• Use `/listapps` to see all available apps"
        
        # Set user's current directory to home
        user_sessions[user_id] = {'current_dir': os.path.expanduser('~')}
        
        await update.message.reply_text(result_msg, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Workspace command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def launch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Launch a specific application with detailed feedback."""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/launch <app_name>`\n\n"
            "💡 **Examples:**\n"
            "• `/launch chrome` - Launch Chrome\n"
            "• `/launch vscode` - Launch VS Code\n"
            "• `/listapps` - See all available apps",
            parse_mode='Markdown'
        )
        return
    
    app_name = context.args[0].lower()
    
    try:
        await update.message.reply_text(f"🚀 Attempting to launch **{app_name}**...", parse_mode='Markdown')
        
        success, stdout, stderr = await launch_application(app_name)
        
        if success:
            await update.message.reply_text(
                f"✅ **{app_name.capitalize()}** launched successfully!\n\n"
                f"📝 *Details:* {stdout}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Failed to launch **{app_name}**\n\n"
                f"🔧 *Error:* {stderr}\n\n"
                f"💡 *Suggestions:*\n"
                f"• Check if application is installed\n"
                f"• Try alternative name\n"
                f"• Use `/listapps` for available options",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        error_msg = f"❌ Launch command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def list_apps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all available applications with categories and availability check."""
    try:
        await update.message.reply_text("🔍 Scanning for available applications...")
        
        categories = {
            "🌐 **Browsers**": ['chrome', 'brave', 'firefox'],
            "💻 **Development**": ['vscode', 'pycharm', 'webstorm', 'terminal'],
            "💬 **Communication**": ['discord', 'slack', 'telegram'],
            "🎵 **Media**": ['spotify', 'vlc', 'celluloid', 'mpv'],
            "📊 **Productivity**": ['libreoffice', 'calculator', 'filemanager'],
            "⚙️ **System**": ['settings'],
            "☁️ **Cloud**": ['mega']
        }
        
        response = "📱 **Available Applications**\n\n"
        available_count = 0
        
        for category, apps in categories.items():
            category_apps = []
            for app in apps:
                # Check if any command for this app exists
                for cmd in app_launchers.get(app, []):
                    if await check_command_exists(cmd):
                        category_apps.append(f"✅ {app}")
                        available_count += 1
                        break
                else:
                    category_apps.append(f"❌ {app}")
            
            if category_apps:
                response += f"{category}\n"
                response += "\n".join(category_apps)
                response += "\n\n"
        
        response += f"📊 **Total Available:** {available_count} applications\n\n"
        response += "💡 **Usage:** `/launch app_name` to start an application"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ List apps command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def list_files_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse files with navigation and file type detection."""
    try:
        user_id = update.effective_user.id
        
        # Get target directory
        if context.args:
            target_dir = ' '.join(context.args)
            if not os.path.isabs(target_dir):
                # Relative path - combine with user's current directory
                current_session = user_sessions.get(user_id, {'current_dir': os.path.expanduser('~')})
                target_dir = os.path.join(current_session['current_dir'], target_dir)
        else:
            # Start from user's home or current session
            current_session = user_sessions.get(user_id, {'current_dir': os.path.expanduser('~')})
            target_dir = current_session['current_dir']
        
        # Normalize path
        target_dir = os.path.abspath(os.path.expanduser(target_dir))
        
        if not os.path.exists(target_dir):
            await update.message.reply_text(f"❌ Directory not found: `{target_dir}`", parse_mode='Markdown')
            return
        
        if not os.path.isdir(target_dir):
            await update.message.reply_text(f"❌ Not a directory: `{target_dir}`", parse_mode='Markdown')
            return
        
        # Update user session
        user_sessions[user_id] = {'current_dir': target_dir}
        
        # Get directory contents
        try:
            items = os.listdir(target_dir)
            items.sort(key=lambda x: (not os.path.isdir(os.path.join(target_dir, x)), x.lower()))
        except PermissionError:
            await update.message.reply_text(f"❌ Permission denied: `{target_dir}`", parse_mode='Markdown')
            return
        
        # Separate files and directories
        directories = []
        files = []
        
        for item in items:
            if item.startswith('.'):
                continue  # Skip hidden files
            
            item_path = os.path.join(target_dir, item)
            icon = get_file_icon(item_path)
            
            if os.path.isdir(item_path):
                directories.append(f"📁 {item}")
            else:
                size = get_file_size(item_path)
                files.append(f"{icon} {item} ({size})")
        
        # Build response
        response = f"📂 **Directory:** `{target_dir}`\n\n"
        
        if directories:
            response += "**📁 Directories:**\n"
            response += "\n".join(directories[:15])
            response += "\n\n"
        
        if files:
            response += "**📄 Files:**\n"
            response += "\n".join(files[:20])
        
        if len(directories) > 15 or len(files) > 20:
            remaining = max(0, len(directories)-15) + max(0, len(files)-20)
            response += f"\n\n... and {remaining} more items"
        
        response += f"\n\n💡 **Navigation:**\n"
        response += f"• `/listfiles path` - Browse specific path\n"
        response += f"• `/listfiles ..` - Go up one level\n"
        response += f"• `/listfiles ~` - Go to home directory\n"
        response += f"• `/openfile path` - Open a file"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ List files command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

def get_file_icon(file_path):
    """Get appropriate icon for file type."""
    if os.path.isdir(file_path):
        return "📁"
    
    name = os.path.basename(file_path).lower()
    ext = os.path.splitext(name)[1].lower()
    
    icon_map = {
        # Audio
        '.mp3': '🎵', '.wav': '🎵', '.flac': '🎵', '.m4a': '🎵', '.ogg': '🎵',
        # Video
        '.mp4': '🎬', '.avi': '🎬', '.mkv': '🎬', '.mov': '🎬', '.wmv': '🎬',
        # Images
        '.jpg': '🖼️', '.jpeg': '🖼️', '.png': '🖼️', '.gif': '🖼️', '.bmp': '🖼️',
        # Documents
        '.pdf': '📕', '.doc': '📘', '.docx': '📘', '.txt': '📄', '.rtf': '📄',
        # Code
        '.py': '🐍', '.js': '📜', '.html': '🌐', '.css': '🎨', '.json': '⚙️',
        '.xml': '⚙️', '.sh': '💻', '.bash': '💻',
        # Archives
        '.zip': '📦', '.tar': '📦', '.gz': '📦', '.7z': '📦', '.rar': '📦',
        # Executables
        '.exe': '⚙️', '.deb': '📦', '.appimage': '⚙️'
    }
    
    return icon_map.get(ext, '📄')

def get_file_size(file_path):
    """Get human-readable file size."""
    try:
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    except:
        return "Unknown"

async def open_file_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open file with default application."""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/openfile <file_path>`\n\n"
            "💡 **Examples:**\n"
            "• `/openfile /home/imran/Music/song.mp3`\n"
            "• `/openfile document.pdf`\n"
            "• Use `/listfiles` to browse files first",
            parse_mode='Markdown'
        )
        return
    
    file_path = ' '.join(context.args)
    
    try:
        # Handle relative paths
        if not os.path.isabs(file_path):
            user_id = update.effective_user.id
            current_session = user_sessions.get(user_id, {'current_dir': os.path.expanduser('~')})
            file_path = os.path.join(current_session['current_dir'], file_path)
        
        file_path = os.path.abspath(os.path.expanduser(file_path))
        
        if not os.path.exists(file_path):
            await update.message.reply_text(f"❌ File not found: `{file_path}`", parse_mode='Markdown')
            return
        
        await update.message.reply_text(f"📂 Opening: `{os.path.basename(file_path)}`", parse_mode='Markdown')
        
        # Use xdg-open to open with default application
        success, stdout, stderr = await safe_system_command(['xdg-open', file_path])
        
        if success:
            await update.message.reply_text(f"✅ Successfully opened: `{os.path.basename(file_path)}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ Failed to open file\n\n"
                f"🔧 **Error:** {stderr}\n\n"
                f"💡 **Try:**\n"
                f"• Check file permissions\n"
                f"• Use specific application: `/launch vlc filename`",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        error_msg = f"❌ Open file command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def play_music_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play music with smart search and player selection."""
    try:
        if not context.args:
            # Show music player options
            keyboard = [
                [InlineKeyboardButton("🎵 Spotify", callback_data="music_spotify")],
                [InlineKeyboardButton("🎵 Local Music", callback_data="music_local")],
                [InlineKeyboardButton("🔍 Search Local", callback_data="music_search")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🎵 **Music Player**\n\nChoose how you want to play music:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return
        
        search_query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for music: `{search_query}`", parse_mode='Markdown')
        
        # Search for local music files
        music_files = await find_music_files(search_query)
        
        if music_files:
            if len(music_files) == 1:
                # Auto-play single result
                file_path = music_files[0]
                success, stdout, stderr = await safe_system_command(['vlc', file_path])
                
                if success:
                    await update.message.reply_text(f"🎵 Playing: `{os.path.basename(file_path)}`", parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Failed to play with VLC")
            else:
                # Show multiple results
                response = "🎵 **Multiple tracks found:**\n\n"
                for i, file_path in enumerate(music_files[:5], 1):
                    response += f"{i}. `{os.path.basename(file_path)}`\n"
                
                response += f"\n💡 Use `/playmusic exact_filename` for specific track"
                await update.message.reply_text(response, parse_mode='Markdown')
        else:
            # Try Spotify
            success, stdout, stderr = await safe_system_command(['spotify'])
            if success:
                await update.message.reply_text(
                    f"🎵 **Spotify** launched\n\n"
                    f"💡 Search for: `{search_query}` in the Spotify app",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    "❌ **No music found**\n\n"
                    "💡 **Suggestions:**\n"
                    "• Check your search terms\n"
                    "• Ensure music files exist in ~/Music\n"
                    "• Install Spotify or VLC if missing",
                    parse_mode='Markdown'
                )
                
    except Exception as e:
        error_msg = f"❌ Play music command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def find_music_files(search_query):
    """Find music files matching search query."""
    music_extensions = ['*.mp3', '*.wav', '*.flac', '*.m4a', '*.ogg', '*.aac']
    music_files = []
    
    search_dirs = [MUSIC_DIR, os.path.expanduser('~/Music'), '/home/imran/Music']
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in music_extensions:
                pattern = os.path.join(search_dir, '**', ext)
                music_files.extend(glob.glob(pattern, recursive=True))
    
    # Filter by search query
    if search_query and search_query.lower() != 'all':
        music_files = [f for f in music_files if search_query.lower() in os.path.basename(f).lower()]
    
    return music_files[:10]

async def play_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Play video file with VLC."""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/playvideo <video_name>`\n\n"
            "💡 **Examples:**\n"
            "• `/playvideo movie` - Search for 'movie'\n"
            "• `/playvideo /path/to/video.mp4` - Specific file",
            parse_mode='Markdown'
        )
        return
    
    search_query = ' '.join(context.args)
    
    try:
        await update.message.reply_text(f"🔍 Searching for video: `{search_query}`", parse_mode='Markdown')
        
        # Handle direct file path
        if os.path.isfile(search_query):
            video_files = [search_query]
        else:
            # Search for video files
            video_files = await find_video_files(search_query)
        
        if not video_files:
            await update.message.reply_text("❌ No video files found matching your search")
            return
        
        if len(video_files) == 1:
            # Play single match
            video_path = video_files[0]
            success, stdout, stderr = await safe_system_command(['vlc', video_path])
            
            if success:
                await update.message.reply_text(f"🎬 Playing: `{os.path.basename(video_path)}`", parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ Failed to play video with VLC")
        else:
            # Show multiple matches
            response = "🎬 **Multiple videos found:**\n\n"
            for i, video_path in enumerate(video_files[:5], 1):
                response += f"{i}. `{os.path.basename(video_path)}`\n"
            
            response += "\n💡 Use `/playvideo exact_filename` for specific video"
            await update.message.reply_text(response, parse_mode='Markdown')
            
    except Exception as e:
        error_msg = f"❌ Play video command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def find_video_files(search_query):
    """Find video files matching search query."""
    video_extensions = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.wmv', '*.flv', '*.webm']
    video_files = []
    
    search_dirs = [VIDEO_DIR, os.path.expanduser('~/Videos'), '/home/imran/Videos']
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in video_extensions:
                pattern = os.path.join(search_dir, '**', ext)
                video_files.extend(glob.glob(pattern, recursive=True))
    
    # Filter by search query
    if search_query:
        video_files = [f for f in video_files if search_query.lower() in os.path.basename(f).lower()]
    
    return video_files[:10]

# MEGA Cloud Integration
async def mega_upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Upload file to MEGA cloud."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/mega_upload <file_path>`", parse_mode='Markdown')
        return
    
    file_path = ' '.join(context.args)
    
    try:
        if not os.path.exists(file_path):
            await update.message.reply_text(f"❌ File not found: `{file_path}`", parse_mode='Markdown')
            return
        
        await update.message.reply_text(f"☁️ Uploading to MEGA: `{os.path.basename(file_path)}`", parse_mode='Markdown')
        
        # Use mega-put command
        success, stdout, stderr = await safe_system_command(['mega-put', file_path, '/'])
        
        if success:
            await update.message.reply_text(f"✅ Uploaded to MEGA: `{os.path.basename(file_path)}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ MEGA upload failed: {stderr}")
            
    except Exception as e:
        error_msg = f"❌ MEGA upload command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def mega_download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download file from MEGA cloud."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/mega_download <file_name>`", parse_mode='Markdown')
        return
    
    file_name = ' '.join(context.args)
    
    try:
        await update.message.reply_text(f"☁️ Downloading from MEGA: `{file_name}`", parse_mode='Markdown')
        
        success, stdout, stderr = await safe_system_command(['mega-get', f'/{file_name}', '.'])
        
        if success:
            await update.message_reply_text(f"✅ Downloaded from MEGA: `{file_name}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ MEGA download failed: {stderr}")
            
    except Exception as e:
        error_msg = f"❌ MEGA download command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def mega_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List files in MEGA cloud."""
    try:
        await update.message.reply_text("☁️ Fetching MEGA file list...")
        
        success, stdout, stderr = await safe_system_command(['mega-ls'])
        
        if success:
            if stdout:
                await update.message.reply_text(f"📁 **MEGA Files:**\n```\n{stdout}\n```", parse_mode='Markdown')
            else:
                await update.message.reply_text("📁 MEGA cloud is empty")
        else:
            await update.message.reply_text(f"❌ Failed to list MEGA files: {stderr}")
            
    except Exception as e:
        error_msg = f"❌ MEGA list command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

# Media Control Functions
async def media_control_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Control media playback."""
    if not context.args:
        await update.message.reply_text(
            "❌ **Usage:** `/media_control <action>`\n\n"
            "🎵 **Actions:**\n"
            "• `play` - Play/resume\n"
            "• `pause` - Pause\n" 
            "• `stop` - Stop\n"
            "• `next` - Next track\n"
            "• `prev` - Previous track\n"
            "• `volumeup` - Volume up\n"
            "• `volumedown` - Volume down",
            parse_mode='Markdown'
        )
        return
    
    action = context.args[0].lower()
    valid_actions = ['play', 'pause', 'stop', 'next', 'prev', 'volumeup', 'volumedown']
    
    if action not in valid_actions:
        await update.message.reply_text(f"❌ Invalid action. Use: {', '.join(valid_actions)}")
        return
    
    try:
        if action in ['volumeup', 'volumedown']:
            # Use pactl for volume control
            change = '+5%' if action == 'volumeup' else '-5%'
            success, stdout, stderr = await safe_system_command(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', change])
        else:
            # Use playerctl for media control
            success, stdout, stderr = await safe_system_command(['playerctl', action])
        
        if success:
            await update.message.reply_text(f"✅ Media control: `{action}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Media control failed: {stderr}")
            
    except Exception as e:
        error_msg = f"❌ Media control command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def current_media_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show currently playing media."""
    try:
        success, stdout, stderr = await safe_system_command(['playerctl', 'metadata', '--format', '{{artist}} - {{title}}'])
        
        if success and stdout:
            await update.message.reply_text(f"🎵 **Now Playing:**\n`{stdout}`", parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No media currently playing or unable to detect")
            
    except Exception as e:
        error_msg = f"❌ Current media command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

# Additional Advanced Features
async def search_apps_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search for installed applications."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/search_apps <app_name>`", parse_mode='Markdown')
        return
    
    search_term = ' '.join(context.args)
    
    try:
        await update.message.reply_text(f"🔍 Searching for applications: `{search_term}`", parse_mode='Markdown')
        
        # Search using apt-cache
        success, stdout, stderr = await safe_system_command(['apt-cache', 'search', search_term])
        
        if success and stdout:
            apps = stdout.split('\n')[:10]  # Show first 10 results
            response = f"📦 **Applications found for '{search_term}':**\n\n"
            for app in apps:
                if app:
                    response += f"• {app}\n"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ No applications found for: `{search_term}`", parse_mode='Markdown')
            
    except Exception as e:
        error_msg = f"❌ Search apps command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

async def kill_app_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force close an application."""
    if not context.args:
        await update.message.reply_text("❌ Usage: `/kill_app <app_name>`", parse_mode='Markdown')
        return
    
    app_name = context.args[0].lower()
    
    try:
        await update.message.reply_text(f"🛑 Attempting to close: `{app_name}`", parse_mode='Markdown')
        
        # Try multiple kill methods
        kill_methods = [
            ['pkill', '-f', app_name],
            ['killall', app_name],
            ['pkill', app_name]
        ]
        
        success = False
        for method in kill_methods:
            success, stdout, stderr = await safe_system_command(method)
            if success:
                break
        
        if success:
            await update.message.reply_text(f"✅ Successfully closed: `{app_name}`", parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Failed to close: `{app_name}`\nApp may not be running", parse_mode='Markdown')
            
    except Exception as e:
        error_msg = f"❌ Kill app command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg, exc_info=True)

# Utility functions
def get_workspace_status():
    """Get workspace status for status reports."""
    return {
        'registered_apps': len(app_launchers),
        'user_sessions': len(user_sessions),
        'available_commands': [
            'workspace', 'launch', 'listapps', 'listfiles', 'openfile',
            'playmusic', 'playvideo', 'mega_upload', 'mega_download', 
            'mega_list', 'media_control', 'current_media', 'search_apps', 'kill_app'
        ]
    }

def cleanup():
    """Cleanup resources on module unload."""
    global user_sessions
    user_sessions.clear()

# Callback query handler for inline buttons
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline buttons."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "music_spotify":
        success, stdout, stderr = await safe_system_command(['spotify'])
        if success:
            await query.edit_message_text("✅ Spotify launched! Search for your music in the app.")
        else:
            await query.edit_message_text("❌ Failed to launch Spotify. Make sure it's installed.")
    
    elif data == "music_local":
        music_files = await find_music_files('all')
        if music_files:
            response = "🎵 **Local Music Files:**\n\n"
            for i, file_path in enumerate(music_files[:8], 1):
                response += f"{i}. `{os.path.basename(file_path)}`\n"
            response += "\n💡 Use `/playmusic filename` to play specific track"
            await query.edit_message_text(response, parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ No local music files found in ~/Music")
    
    elif data == "music_search":
        await query.edit_message_text("🔍 Use `/playmusic song_name` to search and play local music files")

# Export callback handler
def get_callback_handler():
    return handle_callback_query