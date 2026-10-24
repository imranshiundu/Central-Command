# C3NTR@L COMM@ND 🤖

Telegram bot for remote control and monitoring of a Linux machine.
Run commands, manage files, control the system, and keep the bot
auto-restarting via systemd — all from a Telegram chat.

---

## What it actually does

Connect your bot to Telegram (`@BotFather`), authorize your user id or
PIN, and control the host through chat:

- **Core:** `/start`, `/auth <PIN>`, `/help`, `/commands`, `/status`
- **Files:** `/download <url>`, `/listfiles`, `/sendfile <file>`,
  `/deletefile <file>`, `/diskusage`, `/cleanup`
- **System:** `/lock`, `/unlock`, `/shutdown`, `/reboot`, `/sleep`,
  `/msg <text>`, `/speak <text>`
- **Network:** `/ip`, `/wifi`, `/speedtest`, `/ping <host>`,
  `/vpn`, `/netinfo`, `/ports`
- **Security:** `/antitheft`, `/panic`, `/lockdown`, `/geo`, `/alert`
- **Scheduler:** `/schedule <time> <cmd>`, `/tasks`, `/cancel`
- **Workspace:** `/workspace`, `/launch <app>`, `/listapps`,
  `/openfile <file>`, `/playmusic`, `/playvideo`
- **Forensics:** `/browser_history`, `/recover_files`, `/metadata_extract`,
  `/timeline_analysis`, `/clean_evidence`
- **Remote:** `/remote_shell <cmd>`, `/screen_record`, `/webcam_control`
- **System advanced:** `/encrypt_file`, `/decrypt_file`,
  `/system_health`, `/resource_monitor`, and more

Commands that exist in multiple modules are de-duplicated (the first
module to register a name owns it).

## How authorization works

Every module command (`/shutdown`, `/panic`, `/wipe`, `/remote_shell`,
…) requires authorization. Core commands (`/start`, `/auth`, `/help`,
`/commands`, `/status`) are open.

- Pre-authorize users: list their Telegram ids in
  `authorized_user_ids` in `config.json`.
- Temporary access: `/auth <PIN>` with the `admin_pin` from
  `config.json`; sessions expire after `session_timeout_minutes`.
- Unauthorized users cannot run module commands; if `offline_queue` is
  on, their command is queued for later execution.

> ⚠️ Security: set a real `admin_pin` and real `authorized_user_ids`
> before exposing the bot. Tokens and PINs belong in `config.json`,
> which is **gitignored** — never commit them.

---

## Quick start

```bash
git clone https://github.com/imranshiundu/Central-Command.git
cd Central-Command/bot

# 1. Config: copy the example and fill in your bot token
cp config.example.json config.json
# edit config.json: telegram_bot_token, admin_pin, authorized_user_ids

# 2. Dependencies (minimal set - everything else is optional)
python3 -m venv .venv
.venv/bin/pip install -r ../requirements.txt

# 3. Sanity check: every module imports and registers without a token
../.venv/bin/python smoke_test.py

# 4. Run the bot directly (no systemd needed)
.venv/bin/python main.py
```

Get a token: message [@BotFather](https://t.me/botfather) on Telegram,
`/newbot`, copy the token into `config.json`.

### Auto-start on boot (optional, Linux)

```bash
./autostart/setup_autostart.sh
```

This creates a systemd **user** service (`c3ntral-command.service`),
plus desktop autostart and crontab fallbacks, then starts the bot. It
derives all paths from where you cloned the repo — no hardcoded paths.
Manage it with:

```bash
./manage_bot.sh status        # detailed status
./manage_bot.sh diagnostics   # full system diagnostics
./manage_bot.sh logs          # follow logs (systemd journal if available)
./manage_bot.sh start|stop|restart|run|enable|disable
```

## Project structure

```
Central-Command/
├── README.md
├── requirements.txt      # minimal deps (telegram, psutil, requests + job-queue)
├── requirements-optional.txt  # opencv / openai / cryptography for extra features
├── smoke_test.py         # import/registration check (no token needed)
├── bot/
│   ├── config.example.json   # copy to bot/config.json and fill in secrets
│   ├── config.json       # YOUR secrets (gitignored, create from example)
│   ├── manage_bot.sh     # start/stop/status/diagnostics/logs
│   ├── autostart/
│   │   ├── setup_autostart.sh   # one-shot install (systemd + desktop + cron)
│   │   ├── start_bot.sh         # direct launcher with auto-restart monitor
│   │   └── c3ntral-command.service  # systemd unit sample
│   ├── modules/          # feature modules, each registers /commands
│   │   ├── shared.py     # single config + path source of truth
│   │   ├── camera_tools.py
│   │   ├── file_manager.py
│   │   ├── network_tools.py
│   │   ├── network_controller.py
│   │   ├── system_control.py
│   │   ├── system_advanced.py
│   │   ├── scheduler.py
│   │   ├── security_tools.py
│   │   ├── security_monitor.py
│   │   ├── panic_controller.py
│   │   ├── forensics_controller.py
│   │   ├── remote_controller.py
│   │   └── workspace_controller.py
│   └── logs/             # runtime logs (gitignored)
```

## Configuration

`config.example.json` documents every key. `base_dir` may be left empty
— the bot then uses the directory it was cloned into. Feature flags
`enable_<module_name>` turn whole modules on/off.

## Optional features (degrade gracefully)

| Feature | Package | Without it |
|---|---|---|
| Camera / screenshots | `opencv-python` | camera commands disabled |
| Amira AI assistant | `openai` | Amira runs offline |
| File encryption | `cryptography` | `/encrypt_file` disabled |

Install extras with `.venv/bin/pip install -r requirements-optional.txt`.
The bot starts and works without any of them.

## What's not here (and why)

- No web dashboard, no mobile app (listed as future work in the old repo).
- No secrets in git: `config.json`, `*.db`, `logs/`, `data/` and
  `__pycache__/` are all gitignored.
- The orphaned `scripts/` bash implementation was removed — it duplicated
  the Python modules and was never called by anything.

---

## Troubleshooting

```
Bot won't start        → ./manage_bot.sh diagnostics
No systemd session     → .venv/bin/python main.py  (direct run)
Module import fails    → pip install -r requirements.txt
Commands ignored       → check authorized_user_ids / run /auth <PIN>
```

Logs: `bot/logs/bot_console.log`, or `journalctl --user -u c3ntral-command.service -f` when running as a systemd service.

---

## License

MIT — build on it, break it, fix it.
