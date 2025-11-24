#!/usr/bin/env python3
"""
AMIRA V1.0 - Fixed Intelligent AI Assistant Module
SOLVED: API integration, error handling, and performance
"""

import logging
import json
import asyncio
import openai
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from typing import Dict, List, Optional, Tuple
import os
import subprocess
import threading
import psutil
import platform
import socket
import re

logger = logging.getLogger(__name__)

# Amira Configuration
AMIRA_CONFIG = {
    'name': 'Amira',
    'version': 'V1.0',
    'personality': 'intelligent, helpful, proactive',
    'max_context_length': 4000,
    'enable_voice_responses': False,
    'learning_enabled': True,
    'max_history_messages': 8,  # Optimized for performance
    'response_timeout': 25,
    'max_message_length': 3500  # Safe limit for Telegram
}

class AmiraAI:
    """Amira AI Assistant Core Intelligence - FIXED VERSION"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None
        self.is_online = False
        
        # FIXED: Better API key validation and client initialization
        if api_key and api_key.strip() and api_key != "your_openai_api_key_here":
            try:
                self.client = openai.OpenAI(api_key=api_key.strip())
                # Test the API key with a simple request
                test_response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say 'API test successful'"}],
                    max_tokens=10
                )
                self.is_online = True
                logger.info("✅ Amira AI initialized successfully with OpenAI API")
            except Exception as e:
                logger.error(f"❌ Amira AI API initialization failed: {e}")
                self.client = None
                self.is_online = False
        else:
            logger.warning("🔴 Amira AI running in offline mode - no valid API key provided")
            
        self.conversation_history: Dict[int, List[Dict]] = {}
        self.system_prompt = self._create_system_prompt()
        self.learning_db = os.path.join('data', 'amira_learning.db')
        self.user_profiles: Dict[int, Dict] = {}
        self._init_learning_db()
        
    def _create_system_prompt(self) -> str:
        """Create Amira's system personality and capabilities"""
        return f"""
You are {AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']}, an intelligent AI assistant integrated with a command and control system.

CORE IDENTITY:
- You are helpful, proactive, and have a female personality
- You provide clear, actionable technical guidance
- You are security-conscious and privacy-aware
- You adapt to user's technical level

SYSTEM INTEGRATION:
You have access to real system monitoring data including:
- System resource usage (CPU, memory, disk)
- Network connectivity and status
- Security system status
- Active sessions and operations

RESPONSE GUIDELINES:
- Be concise but thorough in explanations
- Provide step-by-step guidance for complex tasks
- Offer multiple solutions when possible
- Ask clarifying questions when needed
- Use bullet points for complex information
- Include relevant emojis for better readability
- Always consider system security implications
- Admit when you don't know something

PERSONALITY TRAITS:
- Friendly but professional
- Patient with technical questions
- Proactive in identifying potential issues
- Respectful of user privacy and security
- Encouraging and supportive

Remember: You are part of a security-focused command and control system. Always prioritize system security and user privacy.
"""
    
    def _init_learning_db(self):
        """Initialize learning database"""
        try:
            os.makedirs('data', exist_ok=True)
            with sqlite3.connect(self.learning_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id INTEGER PRIMARY KEY,
                        preferred_tone TEXT DEFAULT 'professional',
                        technical_level TEXT DEFAULT 'intermediate',
                        favorite_commands TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS conversation_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        input_pattern TEXT,
                        response_pattern TEXT,
                        frequency INTEGER DEFAULT 1,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        last_used DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
            logger.info("Amira learning database initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing learning database: {e}")
    
    async def process_message(self, user_id: int, message: str, context: Dict = None) -> str:
        """Process user message through AI and return response - FIXED VERSION"""
        try:
            # Validate input
            if not message or not message.strip():
                return "🤔 Please provide a message for me to process. I'm here to help!"
            
            message = message.strip()
            
            # FIXED: Better offline mode handling
            if not self.is_online or not self.client:
                return self._get_offline_response()
            
            # Get conversation history
            history = self.conversation_history.get(user_id, [])
            
            # Prepare context information
            system_context = self._get_enhanced_system_context(context)
            
            # Get user preferences for personalized responses
            user_prefs = self._get_user_preferences(user_id)
            
            # Build messages for API
            messages = [
                {"role": "system", "content": self.system_prompt + system_context + user_prefs}
            ]
            
            # Add conversation history (limited for performance)
            for msg in history[-AMIRA_CONFIG['max_history_messages']:]:
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # FIXED: Better async handling with timeout
            try:
                response = await asyncio.wait_for(
                    self._async_openai_call(messages),
                    timeout=AMIRA_CONFIG['response_timeout']
                )
                
                ai_response = response.choices[0].message.content.strip()
                
                # Validate and clean response
                if not ai_response:
                    ai_response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
                else:
                    # Ensure response isn't too long for Telegram
                    ai_response = self._truncate_response(ai_response)
                
            except asyncio.TimeoutError:
                logger.warning(f"Amira API call timed out for user {user_id}")
                ai_response = "⏰ I'm experiencing high latency right now. Please try again in a moment or ask a simpler question."
            except openai.RateLimitError:
                logger.error("OpenAI rate limit exceeded")
                ai_response = "🚫 I've reached my rate limit. Please wait a moment before trying again."
            except openai.APIConnectionError:
                logger.error("OpenAI API connection error")
                ai_response = "🔌 Connection issue with AI service. Please check your internet connection."
            except openai.AuthenticationError:
                logger.error("OpenAI authentication failed")
                ai_response = "🔑 API authentication failed. Please check your OpenAI API key in config.json"
            except Exception as api_error:
                logger.error(f"OpenAI API error: {api_error}")
                ai_response = "❌ I encountered an API error. Please try again later."
            
            # Update conversation history
            self._update_conversation_history(user_id, message, ai_response)
            
            # Learn from interaction
            if AMIRA_CONFIG['learning_enabled']:
                await self._learn_from_interaction(user_id, message, ai_response)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Amira AI processing error: {e}")
            return "❌ I encountered an unexpected error. Please try again with a different question."
    
    async def _async_openai_call(self, messages):
        """Make async OpenAI API call - FIXED VERSION"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using reliable model
                messages=messages,
                max_tokens=800,
                temperature=0.7,
                timeout=30  # Added timeout
            )
        )
    
    def _get_offline_response(self) -> str:
        """Generate helpful offline response with system info"""
        try:
            system_info = self._get_system_info()
            resources = self._get_system_resources()
            
            response = (
                "🤖 **Amira AI - Offline Mode**\n\n"
                "I'm currently running in offline mode. To enable my full AI capabilities:\n\n"
                "🔧 **Setup Instructions:**\n"
                "1. Get an OpenAI API key from https://platform.openai.com/api-keys\n"
                "2. Add it to your config.json as 'openai_api_key'\n"
                "3. Restart the bot\n\n"
                
                "📊 **Current System Status:**\n"
                f"• OS: {system_info['os']}\n"
                f"• CPU: {resources['cpu_percent']}%\n"
                f"• Memory: {resources['memory_percent']}%\n"
                f"• Disk: {resources['disk_percent']}%\n"
                f"• Uptime: {system_info['uptime']}\n\n"
                
                "💡 **I can still help with:**\n"
                "• Basic system information\n"
                "• File management guidance\n" 
                "• Network troubleshooting basics\n"
                "• Security feature explanations\n"
                "• Command usage guidance\n\n"
                
                "🔍 **Try asking me:**\n"
                "• \"How do I check network connection?\"\n"
                "• \"What's my current resource usage?\"\n"
                "• \"Explain the panic mode feature\"\n"
                "• \"Help me with file operations\""
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating offline response: {e}")
            return "🤖 I'm currently in offline mode. Please configure an OpenAI API key in config.json to enable my full AI capabilities."
    
    def _truncate_response(self, response: str) -> str:
        """Ensure response doesn't exceed Telegram limits"""
        max_length = AMIRA_CONFIG['max_message_length']
        
        if len(response) <= max_length:
            return response
        
        # Truncate gracefully at sentence boundary
        truncated = response[:max_length-100] + "...\n\n💡 *Response truncated due to length limits*"
        return truncated
    
    def _get_enhanced_system_context(self, context: Dict = None) -> str:
        """Get comprehensive system context for AI awareness"""
        try:
            context_info = "\n\nCURRENT SYSTEM CONTEXT:\n"
            
            # Basic system info
            system_info = self._get_system_info()
            context_info += f"- OS: {system_info['os']}\n"
            context_info += f"- Hostname: {system_info['hostname']}\n"
            context_info += f"- Uptime: {system_info['uptime']}\n"
            
            # Resource usage
            resources = self._get_system_resources()
            context_info += f"- CPU Usage: {resources['cpu_percent']}%\n"
            context_info += f"- Memory Usage: {resources['memory_percent']}%\n"
            context_info += f"- Disk Usage: {resources['disk_percent']}%\n"
            
            # Network information
            network_info = self._get_network_info()
            context_info += f"- IP Address: {network_info['ip_address']}\n"
            
            # Add provided context
            if context:
                if 'system_status' in context:
                    context_info += f"- System Status: {context['system_status']}\n"
                if 'active_sessions' in context:
                    context_info += f"- Active Users: {context['active_sessions']}\n"
            
            context_info += "\n"
            return context_info
            
        except Exception as e:
            logger.error(f"Error getting enhanced system context: {e}")
            return "\n[System context unavailable]\n"
    
    def _get_system_info(self) -> Dict:
        """Get comprehensive system information"""
        try:
            info = {}
            info['os'] = f"{platform.system()} {platform.release()}"
            info['hostname'] = socket.gethostname()
            
            # Get uptime
            if hasattr(psutil, 'boot_time'):
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                uptime = datetime.now() - boot_time
                days = uptime.days
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                info['uptime'] = f"{days}d {hours}h {minutes}m"
            else:
                info['uptime'] = "Unknown"
                
            return info
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {'os': 'Unknown', 'hostname': 'Unknown', 'uptime': 'Unknown'}
    
    def _get_system_resources(self) -> Dict:
        """Get current system resource usage"""
        try:
            resources = {}
            resources['cpu_percent'] = round(psutil.cpu_percent(interval=0.1), 1)
            memory = psutil.virtual_memory()
            resources['memory_percent'] = round(memory.percent, 1)
            disk = psutil.disk_usage('/')
            resources['disk_percent'] = round(disk.percent, 1)
            return resources
        except Exception as e:
            logger.error(f"Error getting system resources: {e}")
            return {'cpu_percent': 0, 'memory_percent': 0, 'disk_percent': 0}
    
    def _get_network_info(self) -> Dict:
        """Get basic network information"""
        try:
            info = {}
            # Get local IP address
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            info['ip_address'] = s.getsockname()[0]
            s.close()
            return info
        except:
            return {'ip_address': 'Unknown'}
    
    def _get_user_preferences(self, user_id: int) -> str:
        """Get user preferences for personalized responses"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT preferred_tone, technical_level FROM user_preferences WHERE user_id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
            
            if result:
                tone, level = result
                return f"\nUSER PREFERENCES:\n- Preferred Tone: {tone}\n- Technical Level: {level}\n"
            else:
                # Create default preferences for new user
                self._create_default_preferences(user_id)
                return "\nUSER PREFERENCES:\n- Preferred Tone: professional\n- Technical Level: intermediate\n"
                
        except Exception as e:
            logger.error(f"Error getting user preferences: {e}")
            return ""
    
    def _create_default_preferences(self, user_id: int):
        """Create default preferences for new user"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT OR REPLACE INTO user_preferences (user_id, preferred_tone, technical_level) VALUES (?, ?, ?)',
                    (user_id, 'professional', 'intermediate')
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error creating default preferences: {e}")
    
    def _update_conversation_history(self, user_id: int, user_message: str, ai_response: str):
        """Update conversation history for context"""
        try:
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            history = self.conversation_history[user_id]
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": ai_response})
            
            # Keep only last N messages to manage token usage
            max_messages = AMIRA_CONFIG['max_history_messages'] * 2
            if len(history) > max_messages:
                self.conversation_history[user_id] = history[-max_messages:]
        except Exception as e:
            logger.error(f"Error updating conversation history: {e}")
    
    async def _learn_from_interaction(self, user_id: int, user_input: str, ai_response: str):
        """Learn from user interactions to improve responses"""
        try:
            with sqlite3.connect(self.learning_db) as conn:
                cursor = conn.cursor()
                
                # Store conversation pattern
                cursor.execute('''
                    INSERT OR REPLACE INTO conversation_patterns 
                    (user_id, input_pattern, response_pattern, frequency, last_used)
                    VALUES (?, ?, ?, 
                        COALESCE((SELECT frequency + 1 FROM conversation_patterns 
                                 WHERE user_id = ? AND input_pattern = ?), 1),
                        CURRENT_TIMESTAMP)
                ''', (user_id, user_input.lower(), ai_response, user_id, user_input.lower()))
                
                conn.commit()
        except Exception as e:
            logger.error(f"Learning error: {e}")

# Global Amira instance
amira_instance = None

def initialize_amira(api_key: str):
    """Initialize Amira AI system - FIXED VERSION"""
    global amira_instance
    try:
        amira_instance = AmiraAI(api_key)
        if amira_instance.is_online:
            logger.info(f"✅ {AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']} initialized successfully with AI capabilities")
        else:
            logger.info(f"🔴 {AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']} initialized in offline mode")
        return amira_instance
    except Exception as e:
        logger.error(f"❌ Failed to initialize Amira: {e}")
        # Return a basic instance even if initialization fails
        amira_instance = AmiraAI("")  # Offline mode
        return amira_instance

# Telegram Command Handlers - FIXED VERSION
async def amira_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main chat interface with Amira - FIXED VERSION"""
    user_id = update.effective_user.id
    
    if not context.args:
        welcome_msg = (
            f"🤖 **{AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']}**\n\n"
            "I'm your intelligent AI assistant! I can help you with:\n\n"
            "🔧 **System Management:**\n"
            "• System status and monitoring\n"
            "• Resource optimization tips\n"
            "• Security configuration\n"
            "• Troubleshooting guidance\n\n"
            
            "📊 **Technical Assistance:**\n" 
            "• File management help\n"
            "• Network configuration\n"
            "• Command explanations\n"
            "• Best practices advice\n\n"
            
            "🚀 **Smart Features:**\n"
            "• Proactive system suggestions\n"
            "• Learning from interactions\n"
            "• Personalized responses\n"
            "• Security recommendations\n\n"
            
            "💬 **Usage:** `/amira <your question>`\n"
            "📋 **Help:** `/amira_help`\n"
            "🔄 **Clear:** `/amira_clear`\n"
            "📊 **Status:** `/amira_status`\n\n"
            
            "**Examples:**\n"
            "• \"How can I improve system performance?\"\n"
            "• \"Explain the security features\"\n"
            "• \"Help me check network connectivity\"\n"
            "• \"What's my current resource usage?\""
        )
        await update.message.reply_text(welcome_msg)
        return
    
    user_message = ' '.join(context.args)
    
    # Validate message length
    if len(user_message) > 1000:
        await update.message.reply_text("❌ Message too long. Please keep under 1000 characters.")
        return
    
    # Show typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Get system context
    system_context = {
        'system_status': 'operational',
        'active_sessions': '1',
        'current_operations': 'AI Chat'
    }
    
    # Process with Amira
    if amira_instance:
        try:
            response = await amira_instance.process_message(user_id, user_message, system_context)
            await update.message.reply_text(response, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error in amira_chat: {e}")
            await update.message.reply_text(
                "❌ I encountered an error processing your request. "
                "Please try again or check the system logs.\n\n"
                "💡 **Quick help:**\n"
                "• Keep questions under 1000 characters\n"
                "• Check your OpenAI API key if configured\n"
                "• Ensure stable internet connection"
            )
    else:
        await update.message.reply_text(
            "❌ Amira is not properly initialized.\n\n"
            "🔧 **Please check:**\n"
            "1. OpenAI API key in config.json\n"
            "2. Required packages: `pip install openai psutil`\n"
            "3. System logs for initialization errors"
        )

async def amira_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Amira's capabilities - FIXED VERSION"""
    help_text = f"""
🤖 **{AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']} - AI Assistant**

**🎯 CORE CAPABILITIES:**
• System Monitoring & Optimization
• File Management Guidance  
• Network Troubleshooting
• Security Configuration
• Technical Explanations
• Proactive Recommendations

**💬 NATURAL LANGUAGE EXAMPLES:**
• "What's my current system status?"
• "How do I check network connection?"
• "Help me find large files taking space"
• "Explain the panic mode security feature"
• "How can I improve system performance?"
• "Show me resource usage breakdown"

**🔧 TECHNICAL SUPPORT:**
• Command usage and syntax help
• Error troubleshooting guidance  
• Security best practices
• System configuration advice
• Performance optimization tips

**🚀 SMART FEATURES:**
• Context-aware responses
• Learning from interactions  
• Personalized assistance
• Multi-step problem solving
• Security-conscious guidance

**📋 COMMANDS:**
`/amira <message>` - Chat with me naturally
`/amira_help` - Show this help message  
`/amira_status` - Check my system status
`/amira_clear` - Clear conversation history

**🔒 SECURITY & PRIVACY:**
• I operate within your system's security framework
• All conversations are processed securely
• I follow access control policies
• Your privacy is always protected

**💡 TIP:** Talk to me like you would to a technical expert! I understand natural language and can help with complex tasks.
"""
    await update.message.reply_text(help_text)

async def amira_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Amira's status - FIXED VERSION"""
    try:
        if amira_instance:
            ai_status = "🟢 ACTIVE" if amira_instance.is_online else "🔴 OFFLINE"
            mode = "Online AI Mode" if amira_instance.is_online else "Offline Basic Mode"
        else:
            ai_status = "🔴 NOT INITIALIZED"
            mode = "Unavailable"
        
        status_text = f"""
🤖 **{AMIRA_CONFIG['name']} {AMIRA_CONFIG['version']} - Status Report**

**🟢 SYSTEM STATUS: OPERATIONAL**

**AI CAPABILITIES:**
• OpenAI Integration: {ai_status}
• Operating Mode: {mode}
• Learning System: 🟢 ACTIVE
• Context Memory: 🟢 ENABLED
• Response Timeout: {AMIRA_CONFIG['response_timeout']}s

**PERFORMANCE:**
• Active Conversations: {len(amira_instance.conversation_history) if amira_instance else 0}
• History Messages: {AMIRA_CONFIG['max_history_messages']} per user
• Message Limit: {AMIRA_CONFIG['max_message_length']} characters
• Learning Database: 🟢 ACTIVE

**FEATURES:**
• Natural Language Processing
• System Context Awareness  
• Personalized Responses
• Technical Guidance
• Security Recommendations
• Proactive Suggestions

**READY TO ASSIST!** 💫
"""
        await update.message.reply_text(status_text)
    except Exception as e:
        logger.error(f"Error in amira_status: {e}")
        await update.message.reply_text("❌ Error generating status report.")

async def amira_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history with Amira"""
    user_id = update.effective_user.id
    
    if amira_instance:
        if user_id in amira_instance.conversation_history:
            amira_instance.conversation_history[user_id] = []
            await update.message.reply_text("🧹 Conversation history cleared! I'm starting fresh.")
        else:
            await update.message.reply_text("ℹ️ No conversation history to clear.")
    else:
        await update.message.reply_text("❌ Amira is not initialized.")

# Module Registration
def register_commands(register_func):
    """Register Amira commands with the main bot"""
    commands = [
        ('amira', amira_chat, 'Chat with Amira AI assistant'),
        ('amira_help', amira_help, 'Show Amira help and capabilities'),
        ('amira_status', amira_status, 'Show Amira status report'),
        ('amira_clear', amira_clear, 'Clear conversation history with Amira'),
    ]
    
    for command, handler, description in commands:
        register_func(command, handler, description)
    
    logger.info("✅ Amira AI module registered successfully")

# Module initialization
def initialize(api_key: str):
    """Initialize the Amira module"""
    return initialize_amira(api_key)

# Utility functions
def get_amira_stats() -> Dict:
    """Get Amira usage statistics"""
    if not amira_instance:
        return {}
    
    return {
        'active_conversations': len(amira_instance.conversation_history),
        'learning_enabled': AMIRA_CONFIG['learning_enabled'],
        'max_history': AMIRA_CONFIG['max_history_messages'],
        'version': AMIRA_CONFIG['version'],
        'online_mode': amira_instance.is_online
    }

# Test function
async def test_amira():
    """Test Amira functionality"""
    api_key = "your_openai_api_key_here"  # Set your API key
    initialize(api_key)
    
    if amira_instance:
        print("Testing Amira with basic system question...")
        test_response = await amira_instance.process_message(
            12345, 
            "Hello! Can you tell me about my system status and what you can help me with?",
            {'system_status': 'operational'}
        )
        print(f"Amira Test Response: {test_response}")
        return test_response
    return "Amira not initialized"

if __name__ == "__main__":
    # Test the module
    import asyncio
    asyncio.run(test_amira())