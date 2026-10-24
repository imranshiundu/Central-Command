#!/usr/bin/env python3
"""
Shared configuration & path resolution for all C3NTR@L COMM@ND modules.

Every module used to re-implement config loading with its own hardcoded
fallback path, which broke the whole bot when the path was a placeholder
or unwritable. This module is the single source of truth:

- config   : parsed config.json (bot/config.json preferred, CWD fallback)
- BASE_DIR : writable data root (falls back to the bot directory)
- DOWNLOADS_DIR / LOGS_DIR : standard dirs, created at import
- ensure_dir(path) : mkdir that never raises
"""

import json
import logging
import os

_BOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Placeholder values that mean "not configured"
_PLACEHOLDERS = {'', 'file location', '/home/file location', '/home/ file location'}

def _load_config():
    for candidate in (
        os.path.join(_BOT_DIR, 'config.json'),
        os.path.join(os.getcwd(), 'config.json'),
    ):
        try:
            with open(candidate, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
    logging.warning("config.json not found or invalid; using defaults")
    return {}

config = _load_config()

def _resolve_base_dir():
    """Return a writable base directory from config, or fall back to bot dir."""
    raw = str(config.get('paths', {}).get('base_dir', '') or '').strip()
    candidates = []
    if raw and raw.lower() not in {p.lower() for p in _PLACEHOLDERS}:
        candidates.append(os.path.expanduser(raw))
    candidates.append(_BOT_DIR)
    for cand in candidates:
        if os.path.isdir(cand) and os.access(cand, os.W_OK):
            return cand
    return _BOT_DIR

def ensure_dir(path):
    """Create a directory, never raise. Returns a usable path."""
    try:
        os.makedirs(path, exist_ok=True)
        return path
    except OSError:
        fallback = os.path.join(_BOT_DIR, 'data', os.path.basename(os.path.normpath(path)))
        try:
            os.makedirs(fallback, exist_ok=True)
            logging.warning("Could not create %s; using %s", path, fallback)
        except OSError as e:
            logging.error("Could not create %s either: %s", fallback, e)
        return fallback

BASE_DIR = _resolve_base_dir()
DOWNLOADS_DIR = ensure_dir(os.path.join(BASE_DIR, config.get('paths', {}).get('downloads_dir', 'downloads')))
LOGS_DIR = ensure_dir(os.path.join(BASE_DIR, config.get('paths', {}).get('logs_dir', 'logs')))

# Parents used by module databases / data stores
for _sub in (
    os.path.join(BASE_DIR, 'security', 'code_mother'),
    os.path.join(BASE_DIR, 'bot', 'data'),
):
    ensure_dir(_sub)
