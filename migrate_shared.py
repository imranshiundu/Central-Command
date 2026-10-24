#!/usr/bin/env python3
"""One-shot migration: point all modules at modules/shared.py."""
import re
import glob

CONFIG_BLOCK = re.compile(
    r"try:\n"
    r"    with open\('config\.json', 'r'\) as f:\n"
    r"        config = json\.load\(f\)\n"
    r"except FileNotFoundError:\n"
    r"    config = \{\}\n"
    r"    logging\.error\(\"config\.json not found\"\)\n"
)

NAMES = ['BASE_DIR', 'DOWNLOADS_DIR', 'LOGS_DIR']
CONFIG_LINE = {
    name: re.compile(
        "^" + name + r" = os\.path\.join\(BASE_DIR, config\.get\('paths', \{\}\)\.get\('[a-z_]+', '[^']*'\)\)\n",
        re.M,
    )
    for name in NAMES
}

for path in glob.glob('bot/modules/*.py'):
    if path.endswith('shared.py') or path.endswith('forensics_controller1.py'):
        continue
    with open(path) as f:
        src = f.read()

    m = CONFIG_BLOCK.search(src)
    if not m:
        print(f"SKIP (no config block): {path}")
        continue

    # Which config-derived names follow the block?
    tail = src[m.end():]
    found = []
    for name in NAMES:
        if name == 'BASE_DIR':
            if re.search(rf"^BASE_DIR = config\.get\('paths'", tail, re.M):
                found.append(name)
        elif CONFIG_LINE[name].search(tail):
            found.append(name)

    # Remove the BASE_DIR/DOWNLOADS_DIR/LOGS_DIR config-derived lines
    new_tail = tail
    for name in found:
        if name == 'BASE_DIR':
            new_tail = re.sub(r"^BASE_DIR = config\.get\('paths', \{\}\)\.get\('base_dir', '[^']*'\)\n", '', new_tail, count=1, flags=re.M)
        else:
            new_tail = CONFIG_LINE[name].sub('', new_tail, count=1)

    # Redundant re-mkdir of DOWNLOADS_DIR/LOGS_DIR right after (shared creates them)
    new_tail = re.sub(r"\n# Create downloads directory\nos\.makedirs\(DOWNLOADS_DIR, exist_ok=True\)\n", "\n", new_tail, count=1)
    new_tail = re.sub(r"\n# Create logs directory\nos\.makedirs\(LOGS_DIR, exist_ok=True\)\n", "\n", new_tail, count=1)

    import_names = ', '.join(found + ['ensure_dir'])
    shared_import = (
        "try:\n"
        "    from .shared import " + import_names + "\n"
        "except ImportError:  # direct script execution\n"
        "    from shared import " + import_names + "\n"
    )

    src = src[:m.start()] + shared_import + new_tail
    with open(path, 'w') as f:
        f.write(src)
    print(f"OK {path}: {found}")

print("done")
