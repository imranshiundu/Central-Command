#!/bin/bash
# Advanced Media Controller Script

ACTION="$1"
PARAM="$2"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/../logs/media_controller.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check if playerctl is available
if ! command -v playerctl >/dev/null 2>&1; then
    echo "ERROR: playerctl not installed"
    log_message "ERROR: playerctl not installed"
    exit 1
fi

case "$ACTION" in
    "play")
        playerctl play
        log_message "Media: Play"
        echo "▶️ Playing"
        ;;
    "pause")
        playerctl pause
        log_message "Media: Pause"
        echo "⏸️ Paused"
        ;;
    "stop")
        playerctl stop
        log_message "Media: Stop"
        echo "⏹️ Stopped"
        ;;
    "next")
        playerctl next
        log_message "Media: Next"
        echo "⏭️ Next track"
        ;;
    "prev")
        playerctl previous
        log_message "Media: Previous"
        echo "⏮️ Previous track"
        ;;
    "volumeup")
        pactl set-sink-volume @DEFAULT_SINK@ +5%
        log_message "Media: Volume +5%"
        echo "🔊 Volume +5%"
        ;;
    "volumedown")
        pactl set-sink-volume @DEFAULT_SINK@ -5%
        log_message "Media: Volume -5%"
        echo "🔉 Volume -5%"
        ;;
    "status")
        status=$(playerctl status 2>/dev/null || echo "No player")
        if [ "$status" = "Playing" ] || [ "$status" = "Paused" ]; then
            metadata=$(playerctl metadata --format "{{artist}} - {{title}} ({{duration(position)}}/{{duration(mpris:length)}})")
            echo "🎵 $status: $metadata"
            log_message "Media Status: $status - $metadata"
        else
            echo "❌ No media playing"
            log_message "Media Status: No media playing"
        fi
        ;;
    "playfile")
        if [ -n "$PARAM" ] && [ -f "$PARAM" ]; then
            nohup vlc "$PARAM" >/dev/null 2>&1 &
            echo "🎬 Playing: $(basename "$PARAM")"
            log_message "Playing file: $PARAM"
        else
            echo "❌ File not found: $PARAM"
            log_message "ERROR: File not found: $PARAM"
        fi
        ;;
    *)
        echo "Usage: $0 {play|pause|stop|next|prev|volumeup|volumedown|status|playfile}"
        exit 1
        ;;
esac