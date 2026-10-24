#!/usr/bin/env python3
"""Smoke test: import main, load all modules, register commands. No network needed."""
import sys, os, json, types, traceback

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bot'))

# Fresh clone: config.json is gitignored; work from the example
if not os.path.exists('config.json'):
    import shutil
    shutil.copy('config.example.json', 'config.json')

with open('config.json') as f:
    config = json.load(f)

sys.path.insert(0, os.getcwd())

import importlib
mods = ['camera_tools', 'file_manager', 'network_tools', 'system_control', 'scheduler',
        'security_tools', 'workspace_controller', 'panic_controller', 'security_monitor',
        'forensics_controller', 'remote_controller', 'network_controller', 'system_advanced']
loaded, failed = [], []
for m in mods:
    try:
        mod = importlib.import_module(f'modules.{m}')
        if hasattr(mod, 'register_commands'):
            loaded.append(m)
        else:
            failed.append((m, 'NO register_commands'))
    except Exception as e:
        failed.append((m, f'{type(e).__name__}: {e}'))
        traceback.print_exc()

print(f"\nLOADED ({len(loaded)}): {loaded}")
print(f"\nFAILED ({len(failed)}):")
for m, err in failed:
    print(f"  {m}: {err}")

# Try amira (needs openai)
try:
    importlib.import_module('modules.amira')
    print("amira: OK")
except Exception as e:
    print(f"amira: FAILED {type(e).__name__}: {e}")

sys.exit(1 if failed else 0)
