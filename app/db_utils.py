# app/db_utils.py

import sqlanydb
import json
import os
import socket
import logging
import sys
import subprocess
import platform

# Try to import netifaces, but don't fail if not available
try:
    import netifaces
    HAS_NETIFACES = True
except ImportError:
    HAS_NETIFACES = False
    logging.warning("⚠️ netifaces not available - using basic network detection")

logging.basicConfig(
    filename='app.log',
    filemode='w',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_config_path():
    """Get the best-guess path to config.json for EXE and dev environments"""
    if getattr(sys, 'frozen', False):
        # When running from PyInstaller EXE, use the EXE's directory
        base_path = os.path.dirname(sys.executable)
    else:
        # When running normally (script), use script location
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, "config.json")

CONFIG_PATH = get_config_path()

# Hardcoded DB credentials 
DB_USER = "dba"
DB_PASSWORD = "(*$^)"

def get_all_local_ips():
    """Get all possible local IP addresses using multiple methods"""
    ips = []
    
    # Method 1: Using netifaces if available (most reliable)
    if HAS_NETIFACES:
        try:
            for interface in netifaces.interfaces():
                if interface.startswith('lo'):  # Skip loopback
                    continue
                addresses = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addresses:
                    for addr in addresses[netifaces.AF_INET]:
                        ip = addr['addr']
                        if not ip.startswith('127.') and not ip.startswith('169.254.'):
                            if ip not in ips:
                                ips.append(ip)
        except Exception as e:
            logging.warning(f"⚠️ netifaces method failed: {e}")
    
    # Method 2: Platform-specific commands
    try:
        if platform.system() == "Windows":
            # Windows ipconfig
            result = subprocess.run(['ipconfig'], capture_output=True, text=True, timeout=10)
            lines = result.stdout.split('\n')
            for line in lines:
                line = line.strip()
                if 'IPv4 Address' in line and ':' in line:
                    ip = line.split(':')[1].strip()
                    if not ip.startswith('127.') and not ip.startswith('169.254.'):
                        if ip not in ips:
                            ips.append(ip)
        else:
            # Linux/Mac ifconfig or ip command
            try:
                result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=10)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet ' in line and 'scope global' in line:
                        parts = line.strip().split()
                        for part in parts:
                            if '/' in part and not part.startswith('127.') and not part.startswith('169.254.'):
                                ip = part.split('/')[0]
                                if ip not in ips:
                                    ips.append(ip)
            except:
                # Fallback to ifconfig
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=10)
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'inet ' in line and 'netmask' in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[1]
                            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                if ip not in ips:
                                    ips.append(ip)
    except Exception as e:
        logging.warning(f"⚠️ Platform-specific command failed: {e}")
    
    # Method 3: Socket method (fallback)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            if primary_ip not in ips and not primary_ip.startswith('127.'):
                ips.append(primary_ip)
    except Exception as e:
        logging.warning(f"⚠️ Socket method failed: {e}")
    
    # Method 4: Hostname method (backup)
    try:
        hostname = socket.gethostname()
        host_ip = socket.gethostbyname(hostname)
        if host_ip not in ips and not host_ip.startswith('127.'):
            ips.append(host_ip)
    except Exception as e:
        logging.warning(f"⚠️ Hostname method failed: {e}")
    
    # Method 5: getaddrinfo method
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            ip = info[4][0]
            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                if ip not in ips:
                    ips.append(ip)
    except Exception as e:
        logging.warning(f"⚠️ getaddrinfo method failed: {e}")
    
    # Fallback - at least return localhost
    if not ips:
        ips.append("127.0.0.1")
        logging.warning("⚠️ Only localhost IP found - mobile connection may not work")
    
    # Sort IPs by priority (common home networks first)
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
    
    logging.info(f"📡 Found {len(ips)} IP addresses: {ips}")
    return ips

def get_best_local_ip():
    """Get the most likely IP address for mobile device connection"""
    ips = get_all_local_ips()
    
    # Prefer 192.168.1.x (most common home networks)
    wifi_ips = [ip for ip in ips if ip.startswith('192.168.1.')]
    if wifi_ips:
        return wifi_ips[0]
    
    # Then prefer other 192.168.x.x
    wifi_ips = [ip for ip in ips if ip.startswith('192.168.')]
    if wifi_ips:
        return wifi_ips[0]
    
    # Then prefer 10.x.x.x (corporate networks)
    corporate_ips = [ip for ip in ips if ip.startswith('10.')]
    if corporate_ips:
        return corporate_ips[0]
    
    # Return first available
    return ips[0] if ips else "127.0.0.1"

def debug_config_locations():
    """Debug function to find all possible config file locations"""
    possible_paths = []
    
    # Method 1: Current directory
    current_dir = os.getcwd()
    path1 = os.path.join(current_dir, "config.json")
    possible_paths.append(("Current Directory", path1, os.path.exists(path1)))
    
    # Method 2: Script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    path2 = os.path.join(script_dir, "config.json")
    possible_paths.append(("Script Directory", path2, os.path.exists(path2)))
    
    # Method 3: Executable directory (for PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        path3 = os.path.join(exe_dir, "config.json")
        possible_paths.append(("Executable Directory", path3, os.path.exists(path3)))
    
    # Method 4: PyInstaller temp directory
    if hasattr(sys, '_MEIPASS'):
        temp_dir = sys._MEIPASS
        path4 = os.path.join(temp_dir, "config.json")
        possible_paths.append(("PyInstaller Temp", path4, os.path.exists(path4)))
    
    # Method 5: Parent directory
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path5 = os.path.join(parent_dir, "config.json")
    possible_paths.append(("Parent Directory", path5, os.path.exists(path5)))
    
    return possible_paths

def load_config():
    """Load config with extensive debugging"""
    
    # 🔍 DEBUG: Show all possible config locations
    logging.info("🔍 DEBUG: Looking for config.json in these locations:")
    possible_paths = debug_config_locations()
    
    for name, path, exists in possible_paths:
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        logging.info(f"   {name}: {path} - {status}")
        
        # If file exists, show its contents
        if exists:
            try:
                with open(path, 'r') as f:
                    content = json.load(f)
                logging.info(f"      📄 Content: {content}")
            except Exception as e:
                logging.info(f"      ❌ Error reading: {e}")
    
    # Now try to load the config using the original method
    config_path = CONFIG_PATH
    logging.info(f"🎯 Using config path: {config_path}")
    
    try:
        if not os.path.exists(config_path):
            raise Exception(f"❌ Config file not found at: {config_path}")
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logging.info(f"📋 Loaded config content: {config}")
        
        # Get current IP and update ONLY the IP field
        current_ip = get_best_local_ip()
        all_ips = get_all_local_ips()
        
        config["ip"] = current_ip
        config["all_ips"] = all_ips  # Store all IPs for reference
        
        # Write back to config file
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logging.info(f"📡 Updated config with current IP: {current_ip}")
        logging.info(f"📡 All available IPs: {all_ips}")
        logging.info(f"📋 Final DSN from config: {config.get('dsn', 'NOT SET')}")
        return config
        
    except Exception as e:
        logging.error(f"❌ Error loading config from {config_path}: {e}")
        raise Exception(f"Config file error: {e}")

def get_connection():
    """Get database connection using ONLY what's in your config.json"""
    try:
        config = load_config()
        
        # Check if DSN is set in config
        dsn = config.get("dsn")
        if not dsn:
            raise Exception("❌ DSN not found in config.json - please add 'dsn' field")
        
        logging.info(f"🔄 Attempting connection with DSN: {dsn}")
        
        # Try connection with your exact config values
        conn = sqlanydb.connect(
            dsn=dsn,
            userid=DB_USER,
            password=DB_PASSWORD
        )
        
        logging.info(f"✅ Database connection established successfully!")
        logging.info(f"   📋 DSN: {dsn}")
        logging.info(f"   👤 User: {DB_USER}")
        return conn

    except Exception as e:
        # Detailed error reporting
        config = load_config() if 'config' not in locals() else config
        
        logging.error(f"❌ Database connection failed!")
        logging.error(f"   📋 DSN tried: {config.get('dsn', 'NOT SET')}")
        logging.error(f"   👤 User: {DB_USER}")
        logging.error(f"   🔍 Error details: {str(e)}")
        logging.error(f"")
        logging.error(f"🔧 Troubleshooting checklist:")
        logging.error(f"   1. Is SQL Anywhere server running?")
        logging.error(f"   2. Is DSN '{config.get('dsn', 'NOT SET')}' configured correctly?")
        logging.error(f"   3. Can you connect manually with these credentials?")
        logging.error(f"   4. Check Windows ODBC Data Sources for your DSN")
        
        raise Exception(f"Connection failed with DSN '{config.get('dsn', 'NOT SET')}': {str(e)}")

def test_connection():
    """Test function to verify database connection"""
    try:
        print("🧪 Testing database connection...")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        print("✅ Connection test successful!")
        return True
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    # Run connection test when script is executed directly
    print("🔍 Testing network detection...")
    ips = get_all_local_ips()
    print(f"Found IPs: {ips}")
    print(f"Best IP: {get_best_local_ip()}")
    print()
    test_connection()