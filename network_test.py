# network_test.py - Standalone network diagnostic tool
import socket
import subprocess
import platform
import time
import json
import os
import sys

def test_port_connectivity(ip, port=8000):
    """Test if a specific port is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except:
        return False

def get_comprehensive_network_info():
    """Get detailed network information for troubleshooting"""
    info = {
        'platform': platform.system(),
        'hostname': socket.gethostname(),
        'ips': [],
        'firewall_status': 'unknown',
        'port_8000_open': False
    }
    
    print(" NETWORK DIAGNOSTIC TOOL")
    print("=" * 50)
    print(f" Platform: {info['platform']}")
    print(f"  Hostname: {info['hostname']}")
    print()
    
    # Get IP addresses using multiple methods
    print(" DETECTING IP ADDRESSES...")
    
    # Method 1: Socket method
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            info['ips'].append(('Socket Method', primary_ip))
            print(f"    Socket method: {primary_ip}")
    except Exception as e:
        print(f"    Socket method failed: {e}")
    
    # Method 2: Platform-specific commands
    if platform.system() == "Windows":
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'IPv4 Address' in line and ':' in line:
                    ip = line.split(':')[1].strip()
                    if not ip.startswith('127.') and not ip.startswith('169.254.'):
                        info['ips'].append(('Windows ipconfig', ip))
                        print(f"    ipconfig: {ip}")
        except Exception as e:
            print(f"    ipconfig failed: {e}")
    
    # Method 3: Hostname resolution
    try:
        host_ip = socket.gethostbyname(info['hostname'])
        if not host_ip.startswith('127.'):
            info['ips'].append(('Hostname resolution', host_ip))
            print(f"    Hostname: {host_ip}")
    except Exception as e:
        print(f"    Hostname resolution failed: {e}")
    
    # Remove duplicates
    unique_ips = list(set([ip[1] for ip in info['ips']]))
    primary_ip = unique_ips[0] if unique_ips else None
    
    print()
    print(" TESTING CONNECTIVITY...")
    
    if primary_ip:
        print(f" Primary IP: {primary_ip}")
        
        # Test port 8000
        port_open = test_port_connectivity(primary_ip, 8000)
        info['port_8000_open'] = port_open
        
        if port_open:
            print(f"    Port 8000 is accessible on {primary_ip}")
        else:
            print(f"    Port 8000 is NOT accessible on {primary_ip}")
            print(f"      This means mobile devices cannot connect!")
    
    # Test Windows Firewall (if Windows)
    if platform.system() == "Windows":
        print()
        print(" WINDOWS FIREWALL CHECK...")
        try:
            result = subprocess.run(['netsh', 'advfirewall', 'show', 'allprofiles', 'state'], 
                                  capture_output=True, text=True, timeout=10)
            if 'ON' in result.stdout:
                print("   Windows Firewall is ON - may block connections")
                print("      You may need to allow Python through the firewall")
                info['firewall_status'] = 'on'
            else:
                print("    Windows Firewall appears to be OFF")
                info['firewall_status'] = 'off'
        except:
            print("    Could not check Windows Firewall status")
    
    return info, primary_ip

def create_mobile_connection_file(primary_ip, all_ips):
    """Create a simple file with connection instructions"""
    content = f"""MOBILE APP CONNECTION INSTRUCTIONS
========================================

STEP 1: Make sure your phone is on the SAME WiFi network as this computer

 STEP 2: Open your mobile app (IMCSync)

 STEP 3: Try these IPs in order:

PRIMARY IP (try this first):
http://{primary_ip}:8000

ALL AVAILABLE IPs:
"""
    
    for ip in all_ips:
        content += f"http://{ip}:8000\n"
    
    content += f"""
 PASSWORD: IMC-MOBILE

 BROWSER TEST:
Before using the mobile app, test in your computer's browser:
http://{primary_ip}:8000/status

You should see something like:
{{"status": "online", "message": "SyncAnywhere server is running"}}

 TROUBLESHOOTING:
- If browser test fails: Check if server is running
- If mobile app can't connect: Check Windows Firewall
- Try each IP address listed above
- Make sure both devices are on same WiFi (not guest network)

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open("mobile_connection_guide.txt", "w") as f:
        f.write(content)
    
    print(f" Created: mobile_connection_guide.txt")

def main():
    """Main diagnostic function"""
    info, primary_ip = get_comprehensive_network_info()
    
    print()
    print(" SUMMARY")
    print("=" * 50)
    
    if primary_ip:
        print(f" Primary IP for mobile: {primary_ip}:8000")
        
        all_ips = list(set([ip[1] for ip in info['ips']]))
        create_mobile_connection_file(primary_ip, all_ips)
        
        print()
        print(" NEXT STEPS:")
        print("1. Start your SyncAnywhere server")
        print(f"2. Test in browser: http://{primary_ip}:8000/status")
        print("3. If browser works, try mobile app")
        print("4. Use the mobile_connection_guide.txt file for reference")
        
        if not info['port_8000_open']:
            print()
            print("  WARNING: Port 8000 appears blocked!")
            print("   • Check Windows Firewall settings")
            print("   • Allow Python.exe through firewall")
            print("   • Temporarily disable antivirus if needed")
    
    else:
        print(" NO NETWORK IPs FOUND!")
        print("   Check your network connection")
    
    print()
    print(" Full diagnostic info saved to: network_diagnostic.json")
    
    # Save full info to JSON
    with open("network_diagnostic.json", "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")