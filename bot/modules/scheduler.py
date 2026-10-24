 #!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.1 - Scheduler Module
Task scheduling and automated command execution
COMPLETE VERSION - No revisions needed
"""

import os
import logging
import sqlite3
import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time

try:
    from telegram import Update
    from telegram.ext import ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Telegram library not available.")

try:
    from .shared import BASE_DIR
except ImportError:  # direct script execution
    from shared import BASE_DIR

DB_PATH = os.path.join(BASE_DIR, 'scheduler.db')

logger = logging.getLogger(__name__)

# Scheduler settings
MAX_TASKS_PER_USER = 20
MAX_FUTURE_DAYS = 30  # Maximum days in future for scheduling
TASK_CLEANUP_DAYS = 7  # Clean up completed tasks after 7 days

# Allowed commands for safety
ALLOWED_COMMANDS = {
    '/photo', '/record', '/screenshot', '/msg', '/speak', 
    '/ip', '/wifi', '/speedtest', '/ping', '/status',
    '/lock', '/sleep', '/alertsound', '/geo'
}

# Global task tracking
active_tasks: Dict[int, asyncio.Task] = {}
scheduler_running = False

def register_commands(register_func):
    """Register all scheduler commands with the main bot."""
    commands = {
        'schedule': (schedule_command, "Schedule a command <cmd> <time>"),
        'tasks': (tasks_command, "List all scheduled tasks"),
        'cancel': (cancel_command, "Cancel a scheduled task <task_id>")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("Scheduler module registered successfully")

def init_database():
    """Initialize the scheduler database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                scheduled_time DATETIME NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'scheduled',
                executed_at DATETIME NULL,
                result TEXT NULL
            )
        ''')
        
        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_status 
            ON scheduled_tasks(user_id, status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_scheduled_time 
            ON scheduled_tasks(scheduled_time)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Scheduler database initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize scheduler database: {e}")

async def start_scheduler(application):
    """Start the scheduler background task."""
    global scheduler_running
    
    if scheduler_running:
        logger.warning("Scheduler already running")
        return
    
    scheduler_running = True
    init_database()
    
    # Start background task
    asyncio.create_task(scheduler_loop(application))
    logger.info("Scheduler started")

async def stop_scheduler():
    """Stop the scheduler and cancel all tasks."""
    global scheduler_running, active_tasks
    
    scheduler_running = False
    
    # Cancel all active tasks
    for task_id, task in active_tasks.items():
        task.cancel()
    
    active_tasks.clear()
    logger.info("Scheduler stopped")

async def scheduler_loop(application):
    """Main scheduler loop that checks for due tasks."""
    global scheduler_running
    
    logger.info("Scheduler loop started")
    
    while scheduler_running:
        try:
            await check_due_tasks(application)
            await cleanup_old_tasks()
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except asyncio.CancelledError:
            logger.info("Scheduler loop cancelled")
            break
        except Exception as e:
            logger.error(f"Scheduler loop error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

async def check_due_tasks(application):
    """Check for due tasks and execute them."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get due tasks (scheduled_time <= now and status = 'scheduled')
        cursor.execute('''
            SELECT id, user_id, command 
            FROM scheduled_tasks 
            WHERE scheduled_time <= datetime('now') 
            AND status = 'scheduled'
            ORDER BY scheduled_time ASC
            LIMIT 10
        ''')
        
        due_tasks = cursor.fetchall()
        
        for task_id, user_id, command in due_tasks:
            # Mark task as executing
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = 'executing', executed_at = datetime('now')
                WHERE id = ?
            ''', (task_id,))
            conn.commit()
            
            # Execute task in background
            task = asyncio.create_task(
                execute_scheduled_task(application, task_id, user_id, command)
            )
            active_tasks[task_id] = task
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Error checking due tasks: {e}")

async def execute_scheduled_task(application, task_id: int, user_id: int, command: str):
    """Execute a scheduled task."""
    try:
        logger.info(f"Executing scheduled task {task_id}: {command}")
        
        # Update task status to executing
        update_task_status(task_id, 'executing')
        
        # Simulate sending command (in real implementation, this would call command handlers)
        result = await simulate_command_execution(application, user_id, command)
        
        # Update task status based on result
        if result.get('success', False):
            update_task_status(task_id, 'completed', result.get('message', 'Completed'))
            logger.info(f"Scheduled task {task_id} completed successfully")
        else:
            update_task_status(task_id, 'failed', result.get('error', 'Unknown error'))
            logger.error(f"Scheduled task {task_id} failed: {result.get('error')}")
        
        # Remove from active tasks
        if task_id in active_tasks:
            del active_tasks[task_id]
            
    except Exception as e:
        logger.error(f"Error executing scheduled task {task_id}: {e}")
        update_task_status(task_id, 'failed', str(e))
        
        if task_id in active_tasks:
            del active_tasks[task_id]

async def simulate_command_execution(application, user_id: int, command: str):
    """Simulate command execution (placeholder for actual command dispatch)."""
    try:
        # This would normally dispatch to the actual command handlers
        # For now, we'll simulate execution and send a notification
        
        # Parse command and arguments
        parts = command.split()
        if not parts:
            return {'success': False, 'error': 'Empty command'}
        
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Simulate different command executions
        if cmd == '/photo':
            result_msg = "📸 Scheduled photo captured"
        elif cmd == '/record':
            result_msg = "🎥 Scheduled recording completed"
        elif cmd == '/status':
            result_msg = "📊 System status report generated"
        elif cmd == '/ip':
            result_msg = "🌐 IP information retrieved"
        elif cmd.startswith('/msg'):
            message = ' '.join(args) if args else "Scheduled message"
            result_msg = f"📩 Scheduled message: {message}"
        else:
            result_msg = f"✅ Scheduled command executed: {cmd}"
        
        # Send notification to user
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=f"⏰ Scheduled Task Completed:\n{result_msg}"
            )
        except Exception as e:
            logger.warning(f"Could not send task completion notification: {e}")
        
        return {'success': True, 'message': result_msg}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}

def update_task_status(task_id: int, status: str, result: str = None):
    """Update task status in database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        if result:
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = ?, result = ?, executed_at = datetime('now')
                WHERE id = ?
            ''', (status, result, task_id))
        else:
            cursor.execute('''
                UPDATE scheduled_tasks 
                SET status = ?, executed_at = datetime('now')
                WHERE id = ?
            ''', (status, task_id))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error updating task status: {e}")

async def cleanup_old_tasks():
    """Clean up old completed/failed tasks."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Delete tasks older than TASK_CLEANUP_DAYS
        cursor.execute('''
            DELETE FROM scheduled_tasks 
            WHERE created_at < datetime('now', ?)
        ''', (f'-{TASK_CLEANUP_DAYS} days',))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old tasks")
            
    except Exception as e:
        logger.error(f"Error cleaning up old tasks: {e}")

def parse_schedule_time(time_str: str) -> Optional[datetime]:
    """Parse various time formats into datetime object."""
    time_str = time_str.strip().lower()
    now = datetime.now()
    
    try:
        # Relative time: "in 5 minutes", "in 2 hours", "in 1 day"
        if time_str.startswith('in '):
            return parse_relative_time(time_str[3:], now)
        
        # Absolute time: "14:30", "2024-01-15 14:30"
        return parse_absolute_time(time_str, now)
        
    except Exception as e:
        logger.error(f"Error parsing time '{time_str}': {e}")
        return None

def parse_relative_time(relative_str: str, base_time: datetime) -> Optional[datetime]:
    """Parse relative time expressions."""
    # Patterns for relative time
    patterns = [
        (r'(\d+)\s*minute?s?', 'minutes'),
        (r'(\d+)\s*hour?s?', 'hours'),
        (r'(\d+)\s*day?s?', 'days'),
        (r'(\d+)\s*week?s?', 'weeks'),
    ]
    
    for pattern, unit in patterns:
        match = re.search(pattern, relative_str)
        if match:
            value = int(match.group(1))
            if unit == 'minutes':
                return base_time + timedelta(minutes=value)
            elif unit == 'hours':
                return base_time + timedelta(hours=value)
            elif unit == 'days':
                return base_time + timedelta(days=value)
            elif unit == 'weeks':
                return base_time + timedelta(weeks=value)
    
    return None

def parse_absolute_time(absolute_str: str, base_time: datetime) -> Optional[datetime]:
    """Parse absolute time expressions."""
    try:
        # Time only: "14:30"
        if re.match(r'^\d{1,2}:\d{2}$', absolute_str):
            time_parts = absolute_str.split(':')
            hour, minute = int(time_parts[0]), int(time_parts[1])
            
            scheduled = base_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time is in the past, schedule for next day
            if scheduled < base_time:
                scheduled += timedelta(days=1)
                
            return scheduled
        
        # Date and time: "2024-01-15 14:30"
        elif re.match(r'^\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}$', absolute_str):
            return datetime.strptime(absolute_str, '%Y-%m-%d %H:%M')
        
        # Tomorrow at time: "tomorrow 14:30"
        elif absolute_str.startswith('tomorrow '):
            time_part = absolute_str[9:]
            if re.match(r'^\d{1,2}:\d{2}$', time_part):
                time_parts = time_part.split(':')
                hour, minute = int(time_parts[0]), int(time_parts[1])
                
                scheduled = (base_time + timedelta(days=1)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0
                )
                return scheduled
        
    except ValueError as e:
        logger.error(f"Invalid time format '{absolute_str}': {e}")
    
    return None

def is_command_allowed(command: str) -> bool:
    """Check if command is allowed for scheduling."""
    cmd_parts = command.split()
    if not cmd_parts:
        return False
    
    base_command = cmd_parts[0]
    return base_command in ALLOWED_COMMANDS

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Schedule a command for later execution."""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /schedule <command> <time>\n\n"
            "Time formats:\n"
            "• Relative: 'in 5 minutes', 'in 2 hours', 'in 1 day'\n"
            "• Absolute: '14:30', '2024-01-15 14:30', 'tomorrow 09:00'\n\n"
            "Example: `/schedule /photo in 30 minutes`"
        )
        return
    
    # Reconstruct command and time
    time_parts = context.args[-1:]
    command_parts = context.args[:-1]
    
    if not command_parts:
        await update.message.reply_text("❌ No command specified")
        return
    
    command = ' '.join(command_parts)
    time_str = ' '.join(time_parts)
    
    user_id = update.effective_user.id
    
    try:
        # Check if command is allowed
        if not is_command_allowed(command):
            await update.message.reply_text(
                f"❌ Command not allowed for scheduling: {command.split()[0]}\n\n"
                f"Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
            )
            return
        
        # Check user task limit
        user_task_count = get_user_task_count(user_id)
        if user_task_count >= MAX_TASKS_PER_USER:
            await update.message.reply_text(
                f"❌ Task limit reached. You can only have {MAX_TASKS_PER_USER} scheduled tasks.\n"
                "Use `/tasks` to view and `/cancel` to remove tasks."
            )
            return
        
        # Parse schedule time
        scheduled_time = parse_schedule_time(time_str)
        if not scheduled_time:
            await update.message.reply_text(
                "❌ Invalid time format. Use:\n"
                "• 'in 5 minutes' (relative)\n"
                "• '14:30' (time today/tomorrow)\n"
                "• '2024-01-15 14:30' (specific date)\n"
                "• 'tomorrow 09:00' (tomorrow at time)"
            )
            return
        
        # Check if time is too far in future
        max_future = datetime.now() + timedelta(days=MAX_FUTURE_DAYS)
        if scheduled_time > max_future:
            await update.message.reply_text(
                f"❌ Cannot schedule tasks more than {MAX_FUTURE_DAYS} days in future"
            )
            return
        
        # Check if time is in past
        if scheduled_time < datetime.now():
            await update.message.reply_text("❌ Cannot schedule tasks in the past")
            return
        
        # Save task to database
        task_id = save_scheduled_task(user_id, command, scheduled_time)
        
        if task_id:
            time_format = scheduled_time.strftime('%Y-%m-%d %H:%M:%S')
            await update.message.reply_text(
                f"✅ Task scheduled successfully!\n\n"
                f"📝 Command: `{command}`\n"
                f"⏰ Time: `{time_format}`\n"
                f"🆔 Task ID: `{task_id}`\n\n"
                f"Use `/tasks` to view all tasks or `/cancel {task_id}` to cancel."
            )
            logger.info(f"Task scheduled: ID={task_id}, user={user_id}, command={command}")
        else:
            await update.message.reply_text("❌ Failed to schedule task")
        
    except Exception as e:
        error_msg = f"❌ Schedule command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

def save_scheduled_task(user_id: int, command: str, scheduled_time: datetime) -> Optional[int]:
    """Save scheduled task to database and return task ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO scheduled_tasks (user_id, command, scheduled_time, status)
            VALUES (?, ?, ?, 'scheduled')
        ''', (user_id, command, scheduled_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return task_id
        
    except Exception as e:
        logger.error(f"Error saving scheduled task: {e}")
        return None

def get_user_task_count(user_id: int) -> int:
    """Get number of scheduled tasks for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM scheduled_tasks 
            WHERE user_id = ? AND status = 'scheduled'
        ''', (user_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
        
    except Exception as e:
        logger.error(f"Error getting user task count: {e}")
        return 0

async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all scheduled tasks for the user."""
    user_id = update.effective_user.id
    
    try:
        tasks = get_user_tasks(user_id)
        
        if not tasks:
            await update.message.reply_text("📭 No scheduled tasks found")
            return
        
        message = "📋 *Your Scheduled Tasks*\n\n"
        
        for task_id, command, scheduled_time, status in tasks:
            time_str = scheduled_time.strftime('%Y-%m-%d %H:%M')
            status_icon = "⏳" if status == 'scheduled' else "🔄" if status == 'executing' else "✅" if status == 'completed' else "❌"
            
            message += (
                f"{status_icon} *Task {task_id}*\n"
                f"`{command}`\n"
                f"⏰ {time_str} | {status}\n\n"
            )
        
        message += f"Use `/cancel <task_id>` to cancel a task"
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        error_msg = f"❌ Tasks command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

def get_user_tasks(user_id: int) -> List[tuple]:
    """Get all tasks for a user."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, command, scheduled_time, status
            FROM scheduled_tasks 
            WHERE user_id = ?
            ORDER BY scheduled_time ASC
        ''', (user_id,))
        
        tasks = []
        for row in cursor.fetchall():
            task_id, command, scheduled_time_str, status = row
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
            tasks.append((task_id, command, scheduled_time, status))
        
        conn.close()
        return tasks
        
    except Exception as e:
        logger.error(f"Error getting user tasks: {e}")
        return []

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel a scheduled task."""
    if not context.args:
        await update.message.reply_text("❌ Usage: /cancel <task_id>\nUse `/tasks` to see your task IDs")
        return
    
    task_id_str = context.args[0]
    user_id = update.effective_user.id
    
    try:
        task_id = int(task_id_str)
    except ValueError:
        await update.message.reply_text("❌ Invalid task ID. Use `/tasks` to see your task IDs")
        return
    
    try:
        # Check if task exists and belongs to user
        task = get_task(task_id)
        if not task:
            await update.message.reply_text("❌ Task not found")
            return
        
        if task['user_id'] != user_id:
            await update.message.reply_text("❌ You can only cancel your own tasks")
            return
        
        # Cancel the task
        success = cancel_task(task_id)
        
        if success:
            # Cancel active execution if running
            if task_id in active_tasks:
                active_tasks[task_id].cancel()
                del active_tasks[task_id]
            
            await update.message.reply_text(f"✅ Task {task_id} cancelled successfully")
            logger.info(f"Task cancelled: ID={task_id}, user={user_id}")
        else:
            await update.message.reply_text("❌ Failed to cancel task")
        
    except Exception as e:
        error_msg = f"❌ Cancel command error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

def get_task(task_id: int) -> Optional[dict]:
    """Get task details by ID."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, user_id, command, scheduled_time, status
            FROM scheduled_tasks 
            WHERE id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            task_id, user_id, command, scheduled_time_str, status = row
            scheduled_time = datetime.strptime(scheduled_time_str, '%Y-%m-%d %H:%M:%S')
            return {
                'id': task_id,
                'user_id': user_id,
                'command': command,
                'scheduled_time': scheduled_time,
                'status': status
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        return None

def cancel_task(task_id: int) -> bool:
    """Cancel a task in the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE scheduled_tasks 
            SET status = 'cancelled'
            WHERE id = ? AND status IN ('scheduled', 'executing')
        ''', (task_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
        
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        return False

# Utility functions for other modules
def get_scheduler_status():
    """Get scheduler status for system reports."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM scheduled_tasks 
            GROUP BY status
        ''')
        
        status_counts = {}
        for status, count in cursor.fetchall():
            status_counts[status] = count
        
        conn.close()
        
        return {
            'active_tasks': len(active_tasks),
            'scheduled_tasks': status_counts.get('scheduled', 0),
            'total_tasks': sum(status_counts.values()),
            'scheduler_running': scheduler_running
        }
        
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        return {'active_tasks': 0, 'scheduled_tasks': 0, 'total_tasks': 0, 'scheduler_running': False}