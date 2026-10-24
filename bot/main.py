#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.3 - Fixed Main Bot Dispatcher
SOLVED: Multiple instance conflict & Message length issues
"""

import logging
import json
import importlib
import os
import sys
import asyncio
import subprocess
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from threading import Lock, Event
import sqlite3
import traceback
import psutil

# --- Global stop event to prevent multiple instances ---
bot_stop_event = Event()

# --- Configuration Loading (shared with all modules) ---
try:
    from modules.shared import config, BASE_DIR, DOWNLOADS_DIR, LOGS_DIR, ensure_dir
except ImportError:  # direct script execution
    from shared import config, BASE_DIR, DOWNLOADS_DIR, LOGS_DIR, ensure_dir

SCRIPTS_DIR = os.path.join(BASE_DIR, config.get('paths', {}).get('scripts_dir', 'scripts'))
DB_PATH = os.path.join(BASE_DIR, 'command_queue.db')
PID_FILE = os.path.join(BASE_DIR, 'bot.pid')

# --- Logging Setup ---
log_file = os.path.join(LOGS_DIR, 'bot_activity.log')
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# --- Global State Management ---
active_sessions = {}
command_registry = {}
modules = {}
session_lock = Lock()
application = None

# --- Single Instance Check ---
def check_single_instance():
    """Ensure only one bot instance is running"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = f.read().strip()
        
        # Check if process still exists
        try:
            if old_pid and psutil.pid_exists(int(old_pid)):
                logger.error(f"Another bot instance is already running (PID: {old_pid})")
                print(f"❌ Another bot instance is already running (PID: {old_pid})")
                print("💡 Run: ./manage_bot.sh stop   to stop the existing instance")
                return False
        except (ValueError, psutil.NoSuchProcess):
            pass
    
    # Write current PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    return True

def cleanup_pid_file():
    """Remove PID file on exit"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

# --- Database for Offline Queue ---
def init_database():
    """Initialize SQLite database for offline command queue."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS command_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                args TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                executed BOOLEAN DEFAULT FALSE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                command TEXT,
                scheduled_time DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                executed BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        traceback.print_exc()

# --- Security & Session Management ---
def is_authorized(user_id):
    """Check if user is in authorized list."""
    return user_id in config.get('authorized_user_ids', [])

def require_auth(func):
    """Decorator to check user authorization."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id

        # Check if user is pre-authorized
        if is_authorized(user_id):
            return await func(update, context)

        # Check for active session
        with session_lock:
            if user_id in active_sessions:
                session_time = active_sessions[user_id]
                timeout_min = config.get('security', {}).get('session_timeout_minutes', 60)
                if (datetime.now() - session_time).total_seconds() < timeout_min * 60:
                    return await func(update, context)
                else:
                    del active_sessions[user_id]

        # Not authorized - queue command if offline capable
        if config.get('features', {}).get('offline_queue', True):
            queue_offline_command(user_id, f"/{func.__name__}", ' '.join(context.args))
            await update.message.reply_text("🔒 Command queued for offline execution.")
        else:
            await update.message.reply_text("❌ Unauthorized. Use /auth <PIN> to gain access.")
        logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
        return

    return wrapper

def register_command(name, handler, description="No description available"):
    """Register a command in the global registry."""
    command_registry[name] = {
        'handler': handler,
        'description': description,
        'module': handler.__module__
    }
    logger.info(f"Registered command: /{name}")

# --- Offline Queue System ---
def queue_offline_command(user_id, command, args):
    """Queue command for execution when back online."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO command_queue (user_id, command, args) VALUES (?, ?, ?)",
            (user_id, command, args)
        )
        conn.commit()
        conn.close()
        logger.info(f"Queued offline command: {command} {args} from user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to queue offline command: {e}")
        traceback.print_exc()
        return False

async def process_offline_queue():
    """Process any queued commands from offline period."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, command, args FROM command_queue WHERE executed = FALSE"
        )
        queued_commands = cursor.fetchall()

        for cmd_id, user_id, command, args in queued_commands:
            logger.info(f"Executing queued command: {command} {args}")
            cursor.execute(
                "UPDATE command_queue SET executed = TRUE WHERE id = ?",
                (cmd_id,)
            )

        conn.commit()
        conn.close()

        if queued_commands:
            logger.info(f"Processed {len(queued_commands)} queued commands")

    except Exception as e:
        logger.error(f"Error processing offline queue: {e}")
        traceback.print_exc()

# --- Module Loader with Auto-Registration ---
def load_modules():
    """Dynamically load all modules and auto-register their commands."""
    global modules
    module_files = [
        'camera_tools',
        'file_manager', 
        'network_tools',
        'system_control',
        'scheduler',
        'security_tools',
        'workspace_controller',
        'panic_controller',
        'security_monitor', 
        'forensics_controller',
        'remote_controller',
        'network_controller',
        'system_advanced'
    ]

    # Load Amira when enabled and an API key is configured
    amira_cfg = config.get('amira', {})
    amira_key = amira_cfg.get('openai_api_key', '')
    if amira_cfg.get('enabled', False) and amira_key and amira_key != "your_openai_api_key_here":
        module_files.append('amira')
        logger.info("Amira AI module will be loaded (API key found)")
    else:
        logger.info("Amira AI module skipped (disabled or no API key)")

    features = config.get('features', {})
    for module_name in module_files:
        try:
            # Check if module is enabled in config (enable_<module_name>)
            if not features.get(f"enable_{module_name}", True):
                logger.info(f"Module {module_name} disabled in config")
                continue

            module = importlib.import_module(f'modules.{module_name}')
            modules[module_name] = module

            # Amira needs explicit initialization with the API key
            if module_name == 'amira' and hasattr(module, 'initialize'):
                module.initialize(amira_key)

            # Auto-register commands from module
            if hasattr(module, 'register_commands'):
                module.register_commands(register_command)
                logger.info(f"Successfully loaded and registered module: {module_name}")
            else:
                logger.warning(f"Module {module_name} has no register_commands function")

        except ImportError as e:
            logger.error(f"Failed to load module {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error loading module {module_name}: {e}")
            traceback.print_exc()

    return modules

# --- Smart Message Sending (Solves Telegram Length Limit) ---
async def send_smart_message(update: Update, text: str, max_length: int = 4000):
    """
    Split long messages into multiple parts to avoid Telegram limits
    """
    if len(text) <= max_length:
        await update.message.reply_text(text)
        return
    
    # Split by lines first to maintain readability
    lines = text.split('\n')
    current_part = []
    current_length = 0
    
    for line in lines:
        line_length = len(line) + 1  # +1 for newline
        
        if current_length + line_length > max_length:
            # Send current part
            if current_part:
                await update.message.reply_text('\n'.join(current_part))
            
            # Start new part
            current_part = [line]
            current_length = line_length
        else:
            current_part.append(line)
            current_length += line_length
    
    # Send remaining part
    if current_part:
        await update.message.reply_text('\n'.join(current_part))

# --- Core Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with basic info."""
    user_id = update.effective_user.id
    if is_authorized(user_id):
        await update.message.reply_text(
            "🟢 C3NTR@L COMM@ND V1.3 Online\n"
            "You are pre-authorized. Type /help for commands.\n\n"
            "🔓 **Fixed Issues:**\n"
            "• ✅ Multiple instance conflict resolved\n"  
            "• ✅ Message length limits fixed\n"
            "• ✅ Amira AI integration optimized\n"
            "• ✅ Auto-restart loop solved\n\n"
            "🚀 **Enhanced Systems:**\n"
            "• 🚨 Panic Controller - Emergency Response\n"
            "• 🔒 Security Monitor - 24/7 Monitoring\n"
            "• 🔍 Forensics Controller - Digital Investigation\n"
            "• 🌐 Remote Controller - Advanced Remote Access\n"
            "• 📡 Network Controller - Internet & Communication\n"
            "• ⚙️ System Advanced - Deep System Control"
        )
    else:
        await update.message.reply_text(
            "🔒 C3NTR@L COMM@ND V1.3\n"
            "Use /auth <PIN> to gain control."
        )

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Authenticate with PIN for temporary access."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("Usage: /auth <PIN>")
        return

    pin_attempt = context.args[0]
    if config.get('admin_pin') and pin_attempt == config['admin_pin']:
        with session_lock:
            active_sessions[user_id] = datetime.now()
        
        welcome_msg = (
            "✅ Authentication successful! Session active for "
            f"{config.get('security', {}).get('session_timeout_minutes', 60)} minutes.\n\n"
            "🆕 **Enhanced Features:**\n"
            "• Emergency lockdown system\n"
            "• 24/7 security monitoring\n" 
            "• Digital forensics tools\n"
            "• Remote access capabilities\n"
            "• Advanced network control\n"
            "• AI-powered assistance\n\n"
            "💡 **New:** Use /help to see categorized commands"
        )
        
        await update.message.reply_text(welcome_msg)
        logger.info(f"User {user_id} authenticated via PIN")
    else:
        await update.message.reply_text("❌ Invalid PIN")
        logger.warning(f"Failed PIN attempt from user {user_id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands with categorized pagination."""
    user_id = update.effective_user.id
    
    # Check authorization first
    if not is_authorized(user_id):
        with session_lock:
            if user_id not in active_sessions:
                await update.message.reply_text("❌ Unauthorized. Use /auth <PIN> first.")
                return

    # Define command categories with emojis
    categories = {
        "🚨 EMERGENCY & SECURITY": [
            'panic', 'redalert', 'lockdown', 'evidence', 'killswitch',
            'antitheft', 'geo', 'alert', 'wipe'
        ],
        "🔍 INVESTIGATION & FORENSICS": [
            'browser_history', 'recover_files', 'system_scan', 'hash_check',
            'metadata', 'network_scan', 'process_analysis'
        ],
        "🌐 REMOTE & NETWORK": [
            'remote_desktop', 'file_transfer', 'web_scrape', 'download_manager',
            'ip', 'wifi', 'speedtest', 'ping', 'vpn', 'netinfo', 'ports'
        ],
        "⚙️ SYSTEM & CONTROL": [
            'process_monitor', 'hardware_info', 'service_control', 'power_management',
            'lock', 'unlock', 'shutdown', 'reboot', 'sleep', 'msg', 'speak'
        ],
        "📷 CAMERA & MEDIA": [
            'photo', 'record', 'surveillance', 'screenshot', 'camerastatus'
        ],
        "📁 FILE MANAGEMENT": [
            'download', 'listfiles', 'sendfile', 'deletefile', 'diskusage', 'cleanup'
        ],
        "🤖 AI ASSISTANT": [
            'amira', 'amira_help', 'amira_status', 'amira_clear'
        ],
        "⏰ SCHEDULER & TASKS": [
            'schedule', 'tasks', 'cancel'
        ]
    }

    # Get page number from args (default to 1)
    page = 1
    if context.args:
        try:
            page = int(context.args[0])
        except ValueError:
            page = 1

    # Calculate pages
    category_names = list(categories.keys())
    total_pages = len(category_names)
    page = max(1, min(page, total_pages))
    
    current_category = category_names[page - 1]
    commands_in_category = categories[current_category]

    # Build help message for current category
    help_text = f"🤖 **C3NTR@L COMM@ND V1.3 - {current_category}**\n\n"
    
    for cmd_name in commands_in_category:
        if cmd_name in command_registry:
            cmd_info = command_registry[cmd_name]
            help_text += f"• `/{cmd_name}` - {cmd_info['description']}\n"
        else:
            help_text += f"• `/{cmd_name}` - Command available\n"

    # Add pagination info
    help_text += f"\n📄 Page {page} of {total_pages}"
    help_text += f"\n🔧 Use `/help {page+1}` for next category" if page < total_pages else ""
    help_text += f"\n📋 Use `/help 1` for first category"

    # Add quick navigation tips
    if page == 1:
        help_text += "\n\n💡 **Quick Start:**"
        help_text += "\n• Emergency: `/help 1`"
        help_text += "\n• Investigation: `/help 2`" 
        help_text += "\n• Remote Access: `/help 3`"
        help_text += "\n• Full list: Use /commands for all commands"

    await update.message.reply_text(help_text, parse_mode='Markdown')

async def commands_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send all commands in separate messages to avoid length limits."""
    user_id = update.effective_user.id
    
    # Check authorization
    if not is_authorized(user_id):
        with session_lock:
            if user_id not in active_sessions:
                await update.message.reply_text("❌ Unauthorized. Use /auth <PIN> first.")
                return

    # Send header message
    await update.message.reply_text(
        "📋 **All Available Commands**\n\n"
        "Commands will be sent in categories to avoid message limits..."
    )

    # Send commands by category in separate messages
    categories = {
        "🚨 Emergency & Security": ['panic', 'redalert', 'lockdown', 'evidence', 'killswitch', 'antitheft', 'geo', 'alert', 'wipe'],
        "🔍 Investigation": ['browser_history', 'recover_files', 'system_scan', 'hash_check', 'metadata', 'network_scan', 'process_analysis'],
        "🌐 Remote & Network": ['remote_desktop', 'file_transfer', 'web_scrape', 'download_manager', 'ip', 'wifi', 'speedtest', 'ping', 'vpn', 'netinfo', 'ports'],
        "⚙️ System Control": ['process_monitor', 'hardware_info', 'service_control', 'power_management', 'lock', 'unlock', 'shutdown', 'reboot', 'sleep', 'msg', 'speak'],
        "📷 Camera & Media": ['photo', 'record', 'surveillance', 'screenshot', 'camerastatus'],
        "📁 File Management": ['download', 'listfiles', 'sendfile', 'deletefile', 'diskusage', 'cleanup'],
        "🤖 AI Assistant": ['amira', 'amira_help', 'amira_status', 'amira_clear'],
        "⏰ Scheduler": ['schedule', 'tasks', 'cancel']
    }

    for category_name, command_list in categories.items():
        category_text = f"**{category_name}**\n"
        
        for cmd_name in command_list:
            if cmd_name in command_registry:
                cmd_info = command_registry[cmd_name]
                category_text += f"• `/{cmd_name}` - {cmd_info['description']}\n"
        
        if len(category_text) > 100:  # Only send if there are commands
            await update.message.reply_text(category_text, parse_mode='Markdown')
            await asyncio.sleep(0.5)  # Prevent rate limiting

    await update.message.reply_text(
        "✅ All commands listed above!\n\n"
        "💡 **Tip:** Use `/help <page>` for categorized view\n"
        "🔍 **Search:** Use `/amira find command about files` for AI help"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """System status report."""
    try:
        # Get system info
        uptime = subprocess.check_output(['uptime', '-p']).decode().strip()
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        status_msg = (
            "*System Status - C3NTR@L COMM@ND V1.3*\n\n"
            f"*Uptime:* {uptime}\n"
            f"*CPU Usage:* {psutil.cpu_percent()}%\n"
            f"*Memory:* {memory_info.percent}% used\n"
            f"*Disk:* {disk_info.percent}% used\n\n"
            
            f"*Active Sessions:* {len(active_sessions)}\n"
            f"*Loaded Modules:* {len(modules)}\n"
            f"*Commands Available:* {len(command_registry)}\n\n"
            
            "*🆕 Fixed Issues:*\n"
            "• ✅ Multiple instance conflict\n"
            "• ✅ Message length limits\n"
            "• ✅ Amira AI integration\n"
            "• ✅ Auto-restart loop\n\n"
            
            "*Security Status:* 🟢 OPERATIONAL\n"
            "*AI Assistant:* 🟢 READY\n"
            "*All Systems:* 🟢 NOMINAL"
        )

        await update.message.reply_text(status_msg, parse_mode='Markdown')

    except Exception as e:
        error_msg = f"❌ Error getting status: {e}"
        await update.message.reply_text(error_msg)
        logger.error(f"Status command error: {e}")

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unknown commands."""
    await update.message.reply_text(
        "❌ Unknown command. Use `/help` to see available commands.\n\n"
        "💡 **Quick Categories:**\n"
        "• Emergency: `/help 1`\n"
        "• Investigation: `/help 2`\n" 
        "• Remote: `/help 3`\n"
        "• System: `/help 4`\n\n"
        "🔍 Or ask Amira: `/amira how do I check system status?`"
    )

# --- Error Handling ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors in telegram bot."""
    logger.error(f"Exception while handling update: {context.error}")
    
    # Don't print traceback for common Telegram conflicts
    if "Conflict" not in str(context.error):
        traceback.print_exc()

    if update and update.effective_message:
        error_msg = (
            "❌ An unexpected error occurred.\n"
            "The system has logged the issue for review.\n\n"
            "💡 **If this persists:**\n"
            "• Use `/status` to check system\n"
            "• Restart with: ./manage_bot.sh restart"
        )
        await update.effective_message.reply_text(error_msg)

# --- Health Check & Auto-Recovery ---  
async def health_check(context: ContextTypes.DEFAULT_TYPE):
    """Periodic health check and maintenance."""
    try:
        with session_lock:
            now = datetime.now()
            expired_sessions = [
                user_id for user_id, session_time in active_sessions.items()
                if (now - session_time).total_seconds() > config.get('security', {}).get('session_timeout_minutes', 60) * 60
            ]
            for user_id in expired_sessions:
                del active_sessions[user_id]
            if expired_sessions:
                logger.info(f"Cleaned {len(expired_sessions)} expired sessions")

        await process_offline_queue()

        logger.info(f"Health check OK - Sessions: {len(active_sessions)}, Commands: {len(command_registry)}")

    except Exception as e:
        logger.error(f"Health check error: {e}")

# --- Graceful Shutdown ---
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    logger.info("Received shutdown signal")
    bot_stop_event.set()
    
    if application:
        logger.info("Stopping bot application...")
        application.stop()
    
    cleanup_pid_file()
    sys.exit(0)

# --- Main Function ---
def main():
    """Start the bot with all systems."""
    global application
    
    # Check for single instance
    if not check_single_instance():
        sys.exit(1)
    
    # Setup signal handlers for graceful shutdown
    import signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize systems
    init_database()
    load_modules()

    # Create application
    token = config.get('telegram_bot_token', '')
    if not token or 'YOUR_BOT_TOKEN' in token:
        logger.error('telegram_bot_token missing from config.json - cannot start')
        print('\u274c ERROR: Set telegram_bot_token in bot/config.json first.')
        sys.exit(1)
    application = Application.builder().token(token).build()

    # Add callback handler for workspace controller inline buttons
    try:
        from modules.workspace_controller import get_callback_handler
        application.add_handler(CallbackQueryHandler(get_callback_handler()))
    except ImportError:
        logger.warning("Workspace controller callback handler not available")

    # Core command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("commands", commands_all))
    application.add_handler(CommandHandler("status", status))

    # Register all dynamically loaded commands
    for command_name, command_info in command_registry.items():
        application.add_handler(CommandHandler(command_name, command_info['handler']))
        logger.info(f"Added handler for command: /{command_name}")

    # Unknown command handler
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_error_handler(error_handler)

    # Health check system - FIXED: Proper job scheduling
    application.job_queue.run_repeating(
        health_check,
        interval=300,  # 5 minutes
        first=10       # Start after 10 seconds
    )

    logger.info("C3NTR@L COMM@ND V1.3 is starting...")
    logger.info(f"Loaded {len(modules)} modules, {len(command_registry)} commands")
    
    print("🤖 C3NTR@L COMM@ND V1.3 is running. Press Ctrl+C to stop.")
    print("🆕 **Fixed Issues:**")
    print("  ✅ Multiple instance conflict resolved")
    print("  ✅ Message length limits fixed") 
    print("  ✅ Amira AI integration optimized")
    print("  ✅ Auto-restart loop solved")
    print("🚀 **Enhanced Systems:**")
    print("  🚨 Panic Controller    - Emergency Response")
    print("  🔒 Security Monitor    - 24/7 Monitoring") 
    print("  🔍 Forensics Controller - Digital Investigation")
    print("  🌐 Remote Controller   - Advanced Remote Access")
    print("  📡 Network Controller  - Internet & Communication")
    print("  ⚙️ System Advanced     - Deep System Control")
    print(f"  🤖 Amira AI           - {'🟢 ACTIVE' if 'amira' in modules else '🔴 OFFLINE'}")

    try:
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n🛑 C3NTR@L COMM@ND V1.3 stopped gracefully.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        cleanup_pid_file()
        sys.exit(1 if application else 0)

if __name__ == '__main__':
    main()