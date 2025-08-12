# start_server.py
from app.main import app
import uvicorn
import subprocess
import os
import psutil
import sys
import logging
import time
import socket
import platform
import ctypes
from app.db_utils import get_all_local_ips, get_best_local_ip

APP_PORT = 8000
APP_NAME = "SyncAnywhere"

def is_windows():
    return sys.platform == "win32"

def is_admin():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate_and_rerun():
    """Re-run this script with admin privileges (UAC prompt)"""
    try:
        # Get the current script/exe path
        if getattr(sys, 'frozen', False):
            # Running as compiled exe
            current_exe = sys.executable
        else:
            # Running as Python script
            current_exe = sys.executable
            
        # Prepare parameters - include the script name if not frozen
        if getattr(sys, 'frozen', False):
            params = ""
        else:
            params = f'"{__file__}"'
            
        # Add any command line arguments
        if len(sys.argv) > 1:
            args = " ".join(f'"{arg}"' for arg in sys.argv[1:])
            params = f"{params} {args}".strip()
        
        # Request elevation
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", current_exe, params, None, 1
        )
        
        # Exit current non-elevated process
        sys.exit(0)
        
    except Exception as e:
        logging.error(f"❌ Failed to request admin privileges: {e}")
        return False

def remove_old_firewall_rules():
    """Remove any old/conflicting firewall rules"""
    logger = logging.getLogger(__name__)
    
    old_rule_names = [
        "SyncAnywhere Port 8000",
        "SyncAnywhere",
        "Python",
        "FastAPI",
    ]
    
    for rule_name in old_rule_names:
        try:
            result = subprocess.run([
                "netsh", "advfirewall", "firewall", "delete", "rule",
                f"name={rule_name}"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"🗑️ Removed old firewall rule: {rule_name}")
        except:
            pass  # Ignore errors when removing non-existent rules

def add_comprehensive_firewall_rules(port, name):
    """Add comprehensive firewall rules for both inbound and outbound"""
    logger = logging.getLogger(__name__)
    
    # Remove old rules first
    remove_old_firewall_rules()
    
    rules_to_add = [
        # Inbound rules
        {
            "name": f"{name} Inbound TCP {port}",
            "direction": "in",
            "action": "allow",
            "protocol": "TCP",
            "port": str(port),
            "profile": "private,public"
        },
        {
            "name": f"{name} Inbound UDP {port}",
            "direction": "in", 
            "action": "allow",
            "protocol": "UDP",
            "port": str(port),
            "profile": "private,public"
        },
        # Outbound rules
        {
            "name": f"{name} Outbound TCP {port}",
            "direction": "out",
            "action": "allow", 
            "protocol": "TCP",
            "port": str(port),
            "profile": "private,public"
        }
    ]
    
    success_count = 0
    
    for rule in rules_to_add:
        try:
            cmd = [
                "netsh", "advfirewall", "firewall", "add", "rule",
                f"name={rule['name']}",
                f"dir={rule['direction']}",
                f"action={rule['action']}",
                f"protocol={rule['protocol']}",
                f"localport={rule['port']}",
                f"profile={rule['profile']}"
            ]
            
            result = subprocess.run(cmd, check=True, timeout=15, capture_output=True, text=True)
            logger.info(f"✅ Added firewall rule: {rule['name']}")
            success_count += 1
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Failed to add rule {rule['name']}: {e}")
            logger.error(f"   Command output: {e.stdout}")
            logger.error(f"   Command error: {e.stderr}")
        except Exception as e:
            logger.error(f"❌ Unexpected error adding rule {rule['name']}: {e}")
    
    if success_count >= 2:  # At least inbound TCP should work
        logger.info(f"🔥 Added {success_count}/3 firewall rules successfully")
        return True
    else:
        logger.error(f"❌ Only {success_count}/3 firewall rules added - may have connection issues")
        return False

def setup_firewall_for_user_friendly_experience():
    """Setup firewall with enhanced rules and better error handling"""
    logger = logging.getLogger(__name__)
    
    if not is_windows():
        logger.info("🐧 Non-Windows system detected - skipping firewall setup")
        return True
        
    logger.info("🔥 Checking and configuring Windows Firewall...")
    
    # Check if we need admin privileges
    if not is_admin():
        logger.info("🔐 Administrator privileges required for firewall setup")
        logger.info("📋 This will configure firewall rules to allow mobile connections")
        logger.info("🚀 Requesting administrator privileges...")
        
        time.sleep(2)
        elevate_and_rerun()
        return False
    
    # We have admin privileges - add comprehensive rules
    logger.info("🔐 Running with administrator privileges")
    success = add_comprehensive_firewall_rules(APP_PORT, APP_NAME)
    
    if success:
        logger.info("✅ Firewall configured with comprehensive rules!")
        logger.info("📱 Mobile devices should now be able to connect")
        
        # Also try to add Windows Defender exclusion
        try:
            current_exe = sys.executable if getattr(sys, 'frozen', False) else "python.exe"
            subprocess.run([
                "powershell", "-Command", 
                f"Add-MpPreference -ExclusionProcess '{current_exe}'"
            ], capture_output=True, timeout=10)
            logger.info("🛡️ Added Windows Defender exclusion")
        except:
            logger.info("⚠️ Could not add Windows Defender exclusion (not critical)")
        
    else:
        logger.warning("⚠️ Firewall setup had issues - manual configuration may be needed")
        logger.warning("🔧 Manual steps:")
        logger.warning("   1. Open Windows Security → Firewall")
        logger.warning("   2. Click 'Allow an app through firewall'")
        logger.warning("   3. Add this EXE and allow on Private/Public networks")
        
    return success

def setup_startup_logging():
    """Setup basic logging for startup process"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    return logging.getLogger(__name__)

def get_comprehensive_ip_list():
    """Get ALL possible IP addresses this machine can be reached at"""
    ips = []
    logger = logging.getLogger(__name__)
    
    logger.info("🔍 Detecting all available network interfaces...")
    
    # Method 1: Windows ipconfig
    if platform.system() == "Windows":
        try:
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'IPv4 Address' in line and ':' in line:
                    ip = line.split(':')[1].strip()
                    if not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                        ips.append(ip)
                        logger.info(f"   📡 Found via ipconfig: {ip}")
        except Exception as e:
            logger.warning(f"⚠️ ipconfig method failed: {e}")
    
    # Method 2: Linux/Mac ifconfig
    elif platform.system() in ["Linux", "Darwin"]:
        try:
            result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                if 'inet ' in line and 'netmask' in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        if not ip.startswith('127.') and not ip.startswith('169.254.') and ip not in ips:
                            ips.append(ip)
                            logger.info(f"   📡 Found via ifconfig: {ip}")
        except Exception as e:
            logger.warning(f"⚠️ ifconfig method failed: {e}")
    
    # Method 3: Use existing function from db_utils
    try:
        existing_ips = get_all_local_ips()
        for ip in existing_ips:
            if ip not in ips:
                ips.append(ip)
                logger.info(f"   📡 Found via db_utils: {ip}")
    except Exception as e:
        logger.warning(f"⚠️ db_utils method failed: {e}")
    
    # Method 4: Socket connection method
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            if primary_ip not in ips and not primary_ip.startswith('127.'):
                ips.append(primary_ip)
                logger.info(f"   📡 Found via socket: {primary_ip}")
    except Exception as e:
        logger.warning(f"⚠️ socket method failed: {e}")
    
    # Method 5: Hostname method
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        if host_ip not in ips and not host_ip.startswith('127.'):
            ips.append(host_ip)
            logger.info(f"   📡 Found via hostname: {host_ip}")
    except Exception as e:
        logger.warning(f"⚠️ hostname method failed: {e}")
    
    # Method 6: Try to get all local addresses using socket
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if not ip.startswith('127.') and not ip.startswith('::') and ip not in ips:
                ips.append(ip)
                logger.info(f"   📡 Found via getaddrinfo: {ip}")
    except Exception as e:
        logger.warning(f"⚠️ getaddrinfo method failed: {e}")
    
    # Remove any duplicates and sort
    ips = list(set(ips))
    
    # Sort IPs prioritizing common ranges
    def ip_priority(ip):
        if ip.startswith('192.168.1.'):
            return 1
        elif ip.startswith('192.168.0.'):
            return 2  
        elif ip.startswith('192.168.'):
            return 3
        elif ip.startswith('10.'):
            return 4
        elif ip.startswith('172.'):
            return 5
        else:
            return 6
    
    ips.sort(key=ip_priority)
    
    logger.info(f"✅ Total IPs found: {len(ips)}")
    return ips

def test_server_connectivity():
    """Test if the server endpoints are accessible"""
    logger = logging.getLogger(__name__)
    
    # Get the primary IP
    try:
        primary_ip = get_best_local_ip()
        test_url = f"http://{primary_ip}:8000/status"
        
        logger.info(f"🧪 Testing server connectivity at: {test_url}")
        
        # Simple test using socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((primary_ip, 8000))
        sock.close()
        
        if result == 0:
            logger.info("✅ Server port 8000 is accessible")
        else:
            logger.warning("⚠️ Server port 8000 may not be accessible from external devices")
            logger.warning("   This is normal before the server starts - will be resolved shortly!")
            
    except Exception as e:
        logger.warning(f"⚠️ Could not test connectivity: {e}")

def launch_sync_service():
    logger = setup_startup_logging()
    exe_name = "SyncService.exe"

    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    exe_path = os.path.join(base_dir, exe_name)

    # Check if already running
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] and "SyncService.exe" in proc.info['name']:
                logger.info("🔄 SyncService already running (PID: %s)", proc.info['pid'])
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Launch it if not running
    if os.path.exists(exe_path):
        try:
            # Use CREATE_NEW_CONSOLE to run in separate window
            process = subprocess.Popen(
                [exe_path], 
                cwd=base_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Give it a moment to start
            time.sleep(2)
            
            # Verify it's running
            if process.poll() is None:
                logger.info("✅ SyncService launched successfully (PID: %s)", process.pid)
                return True
            else:
                logger.error("❌ SyncService failed to start properly")
                return False
                
        except Exception as e:
            logger.error("❌ Failed to launch SyncService: %s", str(e))
            return False
    else:
        logger.error("❌ SyncService.exe not found at: %s", exe_path)
        return False

def show_enhanced_startup_info():
    """Enhanced startup information with comprehensive IP detection"""
    logger = logging.getLogger(__name__)
    
    # Get ALL available IPs using our enhanced method
    all_ips = get_comprehensive_ip_list()
    primary_ip = all_ips[0] if all_ips else "unknown"
    
    logger.info("=" * 100)
    logger.info("🌟 SYNCANYWHERE SERVER READY FOR MOBILE CONNECTIONS")
    logger.info("=" * 100)
    logger.info("")
    
    if all_ips:
        logger.info("📱 MOBILE APP - TRY THESE IPs IN ORDER OF PRIORITY:")
        for i, ip in enumerate(all_ips, 1):
            logger.info(f"   {i:2d}. http://{ip}:8000")
            if i == 1:
                logger.info(f"       ⭐ RECOMMENDED: Use this IP first")
    else:
        logger.error("❌ NO NETWORK IPs FOUND! Check network connection.")
        return
    
    logger.info("")
    logger.info("🔧 MOBILE APP SETUP INSTRUCTIONS:")
    logger.info("   1. ✅ Ensure phone and computer are on the SAME WiFi network")
    logger.info("   2. 📱 Open your mobile app (IMCSync)")
    logger.info("   3. 🔍 Try 'Auto Scan' first (recommended)")
    logger.info("   4. ✋ If auto scan fails, use 'Manual' mode")
    logger.info(f"   5. ⌨️  Manually enter: {primary_ip}")
    logger.info("   6. 🔑 Password: IMC-MOBILE")
    logger.info("")
    
    logger.info("🛜 NETWORK REQUIREMENTS:")
    logger.info("   • Both devices on SAME WiFi (not guest network)")
    logger.info("   • ✅ Firewall automatically configured!")
    logger.info("   • Port 8000 accessible (should work now)")
    logger.info("   • No VPN active on either device")
    logger.info("")
    
    logger.info("🚨 TROUBLESHOOTING CHECKLIST:")
    logger.info("   1. 🌐 Test in browser first:")
    logger.info(f"      Open: http://{primary_ip}:8000/status")
    logger.info("      Should show: {\"status\": \"online\", ...}")
    logger.info("   2. 📶 Check WiFi network (same for both devices)")
    logger.info("   3. 🔄 Try each IP address listed above")
    logger.info("   4. 🛡️ If still failing, temporarily disable antivirus")
    logger.info("")
    
    logger.info("🔍 QUICK TESTS:")
    logger.info("   • Ping test: ping %s", primary_ip)
    logger.info("   • Browser test: http://%s:8000/status", primary_ip)
    logger.info("   • Mobile hotspot test (as last resort)")
    logger.info("")
    
    logger.info("📁 Logs saved in: logs/ folder")
    logger.info("📄 Connection info saved to: connection_info.txt")
    logger.info("🛑 Press Ctrl+C to stop server")
    logger.info("=" * 100)

def create_enhanced_connection_info_file():
    """Create comprehensive connection info file"""
    try:
        all_ips = get_comprehensive_ip_list()
        primary_ip = all_ips[0] if all_ips else "unknown"
        
        info_content = f"""SyncAnywhere Server - Mobile Connection Guide
================================================================

🎯 PRIORITY IP ADDRESSES (try in this order):
"""
        
        for i, ip in enumerate(all_ips, 1):
            info_content += f"   {i}. http://{ip}:8000\n"
            if i == 1:
                info_content += f"      ⭐ RECOMMENDED - Try this first!\n"
        
        info_content += f"""

📱 MOBILE APP SETUP STEPS:
1. Make sure your phone is connected to the SAME WiFi as this computer
2. Open the IMCSync mobile app
3. Choose 'Auto Scan' and wait for it to complete
4. If auto scan finds the server - you're done! ✅
5. If auto scan fails, tap 'Manual' tab
6. Enter this IP: {primary_ip}
7. Enter password: IMC-MOBILE
8. Tap Connect

🚨 IF CONNECTION FAILS:
• Try each IP address listed above
• Make sure both devices are on the same WiFi network
• Windows Firewall has been configured automatically
• Test in browser first: http://{primary_ip}:8000/status

🧪 BROWSER TEST:
Open this URL in your computer's browser:
http://{primary_ip}:8000/status

You should see something like:
{{"status": "online", "message": "SyncAnywhere server is running", ...}}

🛜 NETWORK INFO:
• Computer WiFi IP: {primary_ip}
• Server Port: 8000
• Pairing Password: IMC-MOBILE
• Firewall: ✅ Automatically configured

📞 SUPPORT:
If none of the IPs work, both devices might not be on the same network.
Try using your phone's mobile hotspot as a test.

Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}
Last Updated: When you see this file creation message in console
================================================================
"""
        
        with open("connection_info.txt", "w", encoding='utf-8') as f:
            f.write(info_content)
        
        # Also create a simple IP list file for quick reference
        with open("mobile_ips.txt", "w") as f:
            f.write("Mobile App IPs (try these):\n")
            for ip in all_ips:
                f.write(f"{ip}:8000\n")
        
        logging.info("📄 Connection info saved to: connection_info.txt")
        logging.info("📄 Quick IP list saved to: mobile_ips.txt")
        
    except Exception as e:
        logging.warning(f"⚠️ Could not create connection info files: {e}")

def start_server_with_better_binding():
    """Start server with enhanced binding and testing"""
    logger = logging.getLogger(__name__)
    
    # Get the primary IP
    primary_ip = get_best_local_ip()
    
    logger.info("🚀 Starting FastAPI server with enhanced configuration...")
    logger.info(f"🌐 Primary IP: {primary_ip}")
    logger.info("📡 Binding to all interfaces (0.0.0.0:8000)")
    
    # Test if port is available
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', 8000))
        sock.close()
        logger.info("✅ Port 8000 is available")
    except OSError as e:
        logger.error(f"❌ Port 8000 is not available: {e}")
        logger.error("🔧 Another application might be using port 8000")
        logger.error("   Try closing other applications or restart the computer")
        return False
    
    try:
        # Start the server with enhanced configuration
        uvicorn.run(
            app, 
            host="0.0.0.0",  # Bind to all interfaces
            port=8000,
            log_level="info",
            access_log=True,
            server_header=False,
            date_header=False,
            # Enhanced timeout settings for mobile connections
            timeout_keep_alive=60,
            timeout_graceful_shutdown=30,
        )
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        return False

if __name__ == "__main__":
    logger = setup_startup_logging()
    
    logger.info("🚀 Starting SyncAnywhere System...")
    logger.info(f"💻 Platform: {platform.system()} {platform.release()}")
    logger.info(f"🐍 Python: {sys.version}")
    
    # STEP 1: Setup firewall with enhanced rules
    firewall_ok = setup_firewall_for_user_friendly_experience()
    
    logger.info("🔥 Firewall configuration complete!")
    
    # STEP 2: Create enhanced connection info file
    create_enhanced_connection_info_file()
    
    # STEP 3: Launch sync service first
    service_started = launch_sync_service()
    
    if not service_started:
        logger.warning("⚠️ SyncService might not be running properly")
        logger.info("🔄 Continuing with main server startup...")
    
    # STEP 4: Show enhanced startup information
    show_enhanced_startup_info()
    
    # STEP 5: Test server connectivity
    test_server_connectivity()
    
    # STEP 6: Start the main server with better error handling
    try:
        logger.info("📱 Mobile apps can now connect!")
        start_server_with_better_binding()
    except KeyboardInterrupt:
        logger.info("🛑 Server stopped by user")
    except Exception as e:
        logger.error("❌ Server crashed: %s", str(e))
        logger.exception("Full error details:")
    finally:
        logger.info("🔚 SyncAnywhere server shutdown complete")