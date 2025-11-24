#!/bin/bash

# C3NTR@L COMM@ND V1.1 - Network Tools Script
# Network diagnostics, monitoring, and troubleshooting
# COMPLETE VERSION - No revisions needed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="/home/imran/snap/C3NTR@L-COMM@ND-V1.1"
LOGS_DIR="$BASE_DIR/logs"
NETWORK_LOG="$LOGS_DIR/network_tools.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Network settings
PING_COUNT=4
PING_TIMEOUT=5
SPEEDTEST_TIMEOUT=60
PORT_SCAN_TIMEOUT=2

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"

# Logging function
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$NETWORK_LOG"
    
    if [ -t 1 ]; then
        case "$level" in
            "ERROR") echo -e "${RED}❌ [ERROR]${NC} $message" ;;
            "SUCCESS") echo -e "${GREEN}✅ [SUCCESS]${NC} $message" ;;
            "WARNING") echo -e "${YELLOW}⚠️ [WARNING]${NC} $message" ;;
            "INFO") echo -e "${BLUE}ℹ️ [INFO]${NC} $message" ;;
            "PROGRESS") echo -e "${CYAN}🔄 [PROGRESS]${NC} $message" ;;
            *) echo "[$level] $message" ;;
        esac
    fi
}

# Error handling
handle_error() {
    log_message "ERROR" "Operation failed: $1"
    exit 1
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Get public IP address
get_public_ip() {
    log_message "INFO" "Retrieving public IP address"
    
    local ip_services=(
        "https://api.ipify.org"
        "https://ident.me"
        "https://checkip.amazonaws.com"
        "https://ipinfo.io/ip"
    )
    
    for service in "${ip_services[@]}"; do
        if command_exists curl; then
            local ip=$(curl -s --connect-timeout 5 "$service")
            if [ -n "$ip" ] && [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                echo "$ip"
                log_message "SUCCESS" "Public IP retrieved: $ip"
                return 0
            fi
        elif command_exists wget; then
            local ip=$(wget -qO- --timeout=5 "$service")
            if [ -n "$ip" ] && [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
                echo "$ip"
                log_message "SUCCESS" "Public IP retrieved: $ip"
                return 0
            fi
        fi
    done
    
    log_message "ERROR" "Failed to retrieve public IP"
    return 1
}

# Get local IP addresses
get_local_ips() {
    log_message "INFO" "Retrieving local IP addresses"
    
    echo -e "${PURPLE}🌐 Local Network Information${NC}"
    echo "=========================================="
    
    # Get default gateway
    if command_exists ip; then
        local gateway=$(ip route | grep default | awk '{print $3}')
        if [ -n "$gateway" ]; then
            echo "Gateway: $gateway"
        fi
    fi
    
    # Get interface information
    if command_exists ip; then
        echo
        echo "Network Interfaces:"
        echo "------------------------------------------"
        ip -o addr show | awk '{print $2, $4}' | while read interface ip; do
            if [[ $ip =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/ ]]; then
                echo "  $interface: $ip"
            fi
        done
    elif command_exists ifconfig; then
        echo
        echo "Network Interfaces:"
        echo "------------------------------------------"
        ifconfig | grep -E "^(eth|wlan|enp|wlp)" | awk '{print $1}' | while read interface; do
            local ip=$(ifconfig "$interface" 2>/dev/null | grep "inet " | awk '{print $2}')
            if [ -n "$ip" ]; then
                echo "  $interface: $ip"
            fi
        done
    fi
    
    # Get DNS servers
    echo
    echo "DNS Servers:"
    echo "------------------------------------------"
    if [ -f /etc/resolv.conf ]; then
        grep "nameserver" /etc/resolv.conf | awk '{print "  "$2}'
    fi
    
    echo "=========================================="
    log_message "SUCCESS" "Local IP information retrieved"
}

# Network connectivity test
test_connectivity() {
    log_message "PROGRESS" "Testing network connectivity"
    
    echo -e "${PURPLE}📡 Network Connectivity Test${NC}"
    echo "=========================================="
    
    local test_hosts=(
        "8.8.8.8"       # Google DNS
        "1.1.1.1"       # Cloudflare DNS
        "google.com"    # Google
        "github.com"    # GitHub
    )
    
    local success_count=0
    local total_count=${#test_hosts[@]}
    
    for host in "${test_hosts[@]}"; do
        echo -n "Testing $host... "
        
        if ping -c 1 -W 2 "$host" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Reachable${NC}"
            ((success_count++))
        else
            echo -e "${RED}❌ Unreachable${NC}"
        fi
    done
    
    echo "------------------------------------------"
    if [ $success_count -eq $total_count ]; then
        echo -e "${GREEN}✅ All connectivity tests passed ($success_count/$total_count)${NC}"
        log_message "SUCCESS" "Network connectivity: $success_count/$total_count tests passed"
    elif [ $success_count -gt 0 ]; then
        echo -e "${YELLOW}⚠️ Partial connectivity ($success_count/$total_count)${NC}"
        log_message "WARNING" "Network connectivity: $success_count/$total_count tests passed"
    else
        echo -e "${RED}❌ No network connectivity${NC}"
        log_message "ERROR" "No network connectivity: 0/$total_count tests passed"
        return 1
    fi
    
    echo "=========================================="
}

# DNS resolution test
test_dns() {
    log_message "PROGRESS" "Testing DNS resolution"
    
    echo -e "${PURPLE}🔍 DNS Resolution Test${NC}"
    echo "=========================================="
    
    local test_domains=(
        "google.com"
        "github.com"
        "ubuntu.com"
        "microsoft.com"
    )
    
    local success_count=0
    local total_count=${#test_domains[@]}
    
    for domain in "${test_domains[@]}"; do
        echo -n "Resolving $domain... "
        
        if command_exists nslookup; then
            if nslookup "$domain" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Resolved${NC}"
                ((success_count++))
            else
                echo -e "${RED}❌ Failed${NC}"
            fi
        elif command_exists dig; then
            if dig +short "$domain" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Resolved${NC}"
                ((success_count++))
            else
                echo -e "${RED}❌ Failed${NC}"
            fi
        else
            # Fallback using getent
            if getent hosts "$domain" >/dev/null 2>&1; then
                echo -e "${GREEN}✅ Resolved${NC}"
                ((success_count++))
            else
                echo -e "${RED}❌ Failed${NC}"
            fi
        fi
    done
    
    echo "------------------------------------------"
    if [ $success_count -eq $total_count ]; then
        echo -e "${GREEN}✅ DNS resolution: $success_count/$total_count successful${NC}"
        log_message "SUCCESS" "DNS resolution: $success_count/$total_count successful"
    else
        echo -e "${YELLOW}⚠️ DNS resolution: $success_count/$total_count successful${NC}"
        log_message "WARNING" "DNS resolution: $success_count/$total_count successful"
    fi
    
    echo "=========================================="
}

# Port connectivity test
test_ports() {
    local host="${1:-localhost}"
    
    log_message "PROGRESS" "Testing common ports on $host"
    
    echo -e "${PURPLE}🚪 Port Connectivity Test - $host${NC}"
    echo "=========================================="
    
    local common_ports=(
        "22"   # SSH
        "80"   # HTTP
        "443"  # HTTPS
        "53"   # DNS
        "21"   # FTP
        "25"   # SMTP
        "110"  # POP3
        "143"  # IMAP
        "993"  # IMAPS
        "995"  # POP3S
    )
    
    local open_ports=()
    
    for port in "${common_ports[@]}"; do
        echo -n "Port $port... "
        
        if command_exists nc; then
            if nc -z -w "$PORT_SCAN_TIMEOUT" "$host" "$port" 2>/dev/null; then
                echo -e "${GREEN}✅ Open${NC}"
                open_ports+=("$port")
            else
                echo -e "${RED}❌ Closed${NC}"
            fi
        elif command_exists telnet; then
            if timeout 2 telnet "$host" "$port" 2>/dev/null | grep -q "Connected"; then
                echo -e "${GREEN}✅ Open${NC}"
                open_ports+=("$port")
            else
                echo -e "${RED}❌ Closed${NC}"
            fi
        else
            # Fallback using /dev/tcp
            if timeout 2 bash -c "echo > /dev/tcp/$host/$port" 2>/dev/null; then
                echo -e "${GREEN}✅ Open${NC}"
                open_ports+=("$port")
            else
                echo -e "${RED}❌ Closed${NC}"
            fi
        fi
    done
    
    echo "------------------------------------------"
    if [ ${#open_ports[@]} -gt 0 ]; then
        echo -e "${GREEN}✅ Open ports: ${open_ports[*]}${NC}"
        log_message "SUCCESS" "Found ${#open_ports[@]} open ports on $host: ${open_ports[*]}"
    else
        echo -e "${YELLOW}⚠️ No common ports open${NC}"
        log_message "INFO" "No common ports open on $host"
    fi
    
    echo "=========================================="
}

# Network speed test
test_speed() {
    log_message "PROGRESS" "Starting network speed test"
    
    echo -e "${PURPLE}🚀 Network Speed Test${NC}"
    echo "=========================================="
    
    # Check if speedtest-cli is available
    if command_exists speedtest-cli; then
        echo "Running speedtest-cli..."
        speedtest-cli --simple --secure
        if [ $? -eq 0 ]; then
            log_message "SUCCESS" "Speed test completed successfully"
        else
            log_message "ERROR" "Speed test failed"
        fi
    else
        echo "speedtest-cli not available. Installing or using fallback..."
        
        # Fallback speed test using curl
        echo "Testing download speed..."
        
        local test_files=(
            "https://proof.ovh.net/files/10Mb.dat"
            "http://ipv4.download.thinkbroadband.com/10MB.zip"
        )
        
        for test_file in "${test_files[@]}"; do
            if command_exists curl; then
                echo "Testing: $(basename "$test_file")"
                local start_time=$(date +%s)
                curl -o /dev/null -w "Downloaded: %{size_download} bytes\nTime: %{time_total} seconds\nSpeed: %{speed_download} bytes/sec\n" "$test_file"
                local end_time=$(date +%s)
                local duration=$((end_time - start_time))
                
                if [ $duration -gt 0 ]; then
                    local speed_mbps=$((8000000 / duration / 1000))  # Approximate Mbps
                    echo "Approximate speed: ${speed_mbps} Mbps"
                fi
                break
            fi
        done
        
        log_message "WARNING" "Used fallback speed test - install speedtest-cli for accurate results"
    fi
    
    echo "=========================================="
}

# WiFi information
get_wifi_info() {
    log_message "PROGRESS" "Gathering WiFi information"
    
    echo -e "${PURPLE}📶 WiFi Information${NC}"
    echo "=========================================="
    
    # Check if WiFi tools are available
    if command_exists nmcli; then
        echo "NetworkManager WiFi Information:"
        echo "------------------------------------------"
        
        # Current connection
        local current_ssid=$(nmcli -t -f active,ssid dev wifi | grep '^yes' | cut -d: -f2)
        if [ -n "$current_ssid" ]; then
            echo "Connected to: $current_ssid"
            
            # Signal strength
            local signal=$(nmcli -t -f active,signal dev wifi | grep '^yes' | cut -d: -f2)
            if [ -n "$signal" ]; then
                echo "Signal strength: $signal%"
                
                # Convert to bars
                local bars=$((signal / 20))
                local bar_str=""
                for ((i=1; i<=5; i++)); do
                    if [ $i -le $bars ]; then
                        bar_str="${bar_str}▮"
                    else
                        bar_str="${bar_str}▯"
                    fi
                done
                echo "Signal bars: $bar_str"
            fi
        else
            echo "Not connected to WiFi"
        fi
        
        echo
        echo "Available Networks:"
        echo "------------------------------------------"
        nmcli -t -f ssid,signal,security dev wifi | head -10 | while IFS=: read -r ssid signal security; do
            if [ -n "$ssid" ] && [ "$ssid" != "--" ]; then
                local bars=$((signal / 20))
                local bar_str=""
                for ((i=1; i<=5; i++)); do
                    if [ $i -le $bars ]; then
                        bar_str="${bar_str}▮"
                    else
                        bar_str="${bar_str}▯"
                    fi
                done
                printf "%-20s %-6s %s\n" "$ssid" "$bar_str" "$security"
            fi
        done
        
    elif command_exists iwconfig; then
        echo "iwconfig WiFi Information:"
        echo "------------------------------------------"
        iwconfig 2>/dev/null | grep -v "no wireless" | while read -r line; do
            echo "  $line"
        done
        
    else
        echo "WiFi tools not available"
        log_message "WARNING" "WiFi information tools not available"
    fi
    
    echo "=========================================="
    log_message "SUCCESS" "WiFi information retrieved"
}

# Network interface statistics
get_interface_stats() {
    log_message "PROGRESS" "Gathering network interface statistics"
    
    echo -e "${PURPLE}📊 Network Interface Statistics${NC}"
    echo "=========================================="
    
    if command_exists ip; then
        echo "Interface Statistics:"
        echo "------------------------------------------"
        ip -s link show | grep -E "^[0-9]+:" -A 2 | while read -r line; do
            echo "  $line"
        done
    elif [ -f /proc/net/dev ]; then
        echo "Network Device Statistics:"
        echo "------------------------------------------"
        cat /proc/net/dev | head -10
    fi
    
    # Show connection statistics
    if command_exists ss; then
        echo
        echo "Connection Statistics:"
        echo "------------------------------------------"
        ss -s
    elif command_exists netstat; then
        echo
        echo "Connection Statistics:"
        echo "------------------------------------------"
        netstat -s | head -20
    fi
    
    echo "=========================================="
    log_message "SUCCESS" "Interface statistics retrieved"
}

# Trace route to host
trace_route() {
    local host="${1:-8.8.8.8}"
    
    log_message "PROGRESS" "Tracing route to $host"
    
    echo -e "${PURPLE}🛣️  Trace Route to $host${NC}"
    echo "=========================================="
    
    if command_exists traceroute; then
        traceroute -w 2 -q 1 -m 15 "$host"
    elif command_exists tracepath; then
        tracepath "$host"
    elif command_exists mtr; then
        mtr --report --report-cycles 1 "$host"
    else
        echo "No trace route tools available (traceroute, tracepath, or mtr)"
        log_message "WARNING" "Trace route tools not available"
        return 1
    fi
    
    local result=$?
    if [ $result -eq 0 ]; then
        log_message "SUCCESS" "Trace route to $host completed"
    else
        log_message "ERROR" "Trace route to $host failed"
    fi
    
    echo "=========================================="
}

# VPN status check
check_vpn_status() {
    log_message "PROGRESS" "Checking VPN status"
    
    echo -e "${PURPLE}🛡️ VPN Status Check${NC}"
    echo "=========================================="
    
    local vpn_detected=false
    
    # Check for common VPN interfaces
    if command_exists ip; then
        local vpn_interfaces=$(ip addr show | grep -E "(tun|tap|wg|ppp)" | wc -l)
        if [ $vpn_interfaces -gt 0 ]; then
            echo "VPN Interfaces detected:"
            ip addr show | grep -E "^[0-9]+: (tun|tap|wg|ppp)" | awk '{print "  "$2}'
            vpn_detected=true
        fi
    fi
    
    # Check for VPN processes
    local vpn_processes=$(ps aux | grep -E "(openvpn|wireguard|wg|vpn)" | grep -v grep | wc -l)
    if [ $vpn_processes -gt 0 ]; then
        echo "VPN Processes running:"
        ps aux | grep -E "(openvpn|wireguard|wg|vpn)" | grep -v grep | awk '{print "  "$11}'
        vpn_detected=true
    fi
    
    # Check for VPN routes
    if command_exists ip; then
        local vpn_routes=$(ip route show | grep -E "(tun|tap|wg|ppp)" | wc -l)
        if [ $vpn_routes -gt 0 ]; then
            echo "VPN Routes configured"
            vpn_detected=true
        fi
    fi
    
    if [ "$vpn_detected" = true ]; then
        echo -e "${GREEN}✅ VPN activity detected${NC}"
        log_message "SUCCESS" "VPN activity detected"
    else
        echo -e "${YELLOW}⚠️ No VPN detected${NC}"
        log_message "INFO" "No VPN detected"
    fi
    
    echo "=========================================="
}

# Comprehensive network diagnostics
network_diagnostics() {
    log_message "INFO" "Starting comprehensive network diagnostics"
    
    echo -e "${CYAN}🛠️  Comprehensive Network Diagnostics${NC}"
    echo "=========================================="
    echo
    
    # Public IP information
    echo -e "${BLUE}1. Public IP Information${NC}"
    local public_ip=$(get_public_ip)
    if [ -n "$public_ip" ]; then
        echo "Public IP: $public_ip"
    else
        echo "Public IP: Unable to determine"
    fi
    echo
    
    # Local network information
    echo -e "${BLUE}2. Local Network Information${NC}"
    get_local_ips
    echo
    
    # Connectivity test
    echo -e "${BLUE}3. Connectivity Test${NC}"
    test_connectivity
    echo
    
    # DNS test
    echo -e "${BLUE}4. DNS Resolution Test${NC}"
    test_dns
    echo
    
    # Port test (localhost)
    echo -e "${BLUE}5. Local Port Test${NC}"
    test_ports "localhost"
    echo
    
    # WiFi information
    echo -e "${BLUE}6. WiFi Information${NC}"
    get_wifi_info
    echo
    
    # Interface statistics
    echo -e "${BLUE}7. Interface Statistics${NC}"
    get_interface_stats
    echo
    
    # VPN status
    echo -e "${BLUE}8. VPN Status${NC}"
    check_vpn_status
    echo
    
    log_message "SUCCESS" "Comprehensive network diagnostics completed"
    echo -e "${GREEN}🎉 Network diagnostics completed successfully!${NC}"
    echo "=========================================="
}

# Main function
main() {
    local action="${1:-diagnostics}"
    
    case "$action" in
        "public-ip")
            get_public_ip
            ;;
        "local-ips")
            get_local_ips
            ;;
        "connectivity")
            test_connectivity
            ;;
        "dns")
            test_dns
            ;;
        "ports")
            test_ports "$2"
            ;;
        "speed")
            test_speed
            ;;
        "wifi")
            get_wifi_info
            ;;
        "stats")
            get_interface_stats
            ;;
        "traceroute")
            trace_route "$2"
            ;;
        "vpn")
            check_vpn_status
            ;;
        "diagnostics")
            network_diagnostics
            ;;
        "help"|"--help"|"-h")
            echo -e "${CYAN}C3NTR@L COMM@ND Network Tools${NC}"
            echo "=========================================="
            echo "Usage: $0 [command] [host]"
            echo
            echo "Commands:"
            echo "  public-ip     - Get public IP address"
            echo "  local-ips     - Get local IP addresses and network info"
            echo "  connectivity  - Test network connectivity"
            echo "  dns           - Test DNS resolution"
            echo "  ports [host]  - Test common ports (default: localhost)"
            echo "  speed         - Test network speed"
            echo "  wifi          - Show WiFi information"
            echo "  stats         - Show network interface statistics"
            echo "  traceroute [host] - Trace route to host (default: 8.8.8.8)"
            echo "  vpn           - Check VPN status"
            echo "  diagnostics   - Run comprehensive diagnostics (default)"
            echo "  help          - Show this help message"
            echo
            echo "Examples:"
            echo "  $0 diagnostics          # Full network diagnostics"
            echo "  $0 ports google.com     # Test ports on google.com"
            echo "  $0 traceroute github.com # Trace route to github.com"
            echo "  $0 speed                # Test network speed"
            ;;
        *)
            echo -e "${RED}Unknown command: $action${NC}"
            echo "Use '$0 help' for available commands"
            return 1
            ;;
    esac
}

# If script is executed directly, run main function
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    log_message "INFO" "Network tools script started with arguments: $*"
    main "$@"
    exit $?
fi