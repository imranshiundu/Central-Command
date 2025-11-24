#!/bin/bash
# Advanced File Browser Script

DIR="${1:-$HOME}"
MAX_ITEMS=20

list_directory() {
    local dir="$1"
    
    if [ ! -d "$dir" ]; then
        echo "ERROR: Directory not found: $dir"
        return 1
    fi
    
    if [ ! -r "$dir" ]; then
        echo "ERROR: Permission denied: $dir"
        return 1
    fi
    
    echo "📂 Directory: $dir"
    echo "=========================================="
    
    # List directories
    echo "📁 Directories:"
    find "$dir" -maxdepth 1 -type d -not -path "$dir" -exec basename {} \; | head -n $MAX_ITEMS | while read -r item; do
        echo "  📁 $item"
    done
    
    echo ""
    
    # List files with icons
    echo "📄 Files:"
    find "$dir" -maxdepth 1 -type f -exec basename {} \; | head -n $MAX_ITEMS | while read -r item; do
        case "$item" in
            *.mp3|*.wav|*.flac) echo "  🎵 $item" ;;
            *.mp4|*.avi|*.mkv) echo "  🎬 $item" ;;
            *.jpg|*.png|*.gif) echo "  🖼️ $item" ;;
            *.pdf) echo "  📕 $item" ;;
            *.doc|*.docx) echo "  📘 $item" ;;
            *.txt|*.md) echo "  📄 $item" ;;
            *.py) echo "  🐍 $item" ;;
            *.sh) echo "  💻 $item" ;;
            *.zip|*.tar|*.gz) echo "  📦 $item" ;;
            *) echo "  📄 $item" ;;
        esac
    done
    
    local total_items=$(find "$dir" -maxdepth 1 | wc -l)
    echo "=========================================="
    echo "Total items: $((total_items - 1))"
}

list_directory "$DIR"