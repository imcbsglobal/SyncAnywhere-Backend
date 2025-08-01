# smart_launcher.py
import os
import sys
import time
import psutil
import subprocess
import socket
import threading
import json
from datetime import datetime, timedelta

class SmartLauncher:
    def __init__(self):
        self.base_dir = self.get_base_directory()
        self.server_process = None
        self.last_activity = datetime.now()
        self.idle_timeout = 30 * 60  # 30 minutes
        self.check_interval = 60  # Check every minute
        self.port = 8000
        
    def get_base_directory(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))
            
    def log(self, message):
        """Simple logging"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")
        
        # Also log to file
        log_file = os.path.join(self.base_dir, "launcher.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    
    def is_port_in_use(self, port):
        """Check if port is already in use"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        except:
            return False
    
    def has_active_connections(self):
        """Check for active connections on our port"""
        try:
            for conn in psutil.net_connections():
                if (conn.laddr.port == self.port and 
                    conn.status in ['ESTABLISHED', 'SYN_RECV']):
                    return True
            return False
        except:
            return False
    
    def start_server(self):
        """Start the FastAPI server"""
        if self.server_process and self.server_process.poll() is None:
            self.log("🔄 Server already running")
            return True
            
        try:
            server_exe = os.path.join(self.base_dir, "SyncAnywhere.exe")
            if not os.path.exists(server_exe):
                self.log(f"❌ Server executable not found: {server_exe}")
                return False
            
            # Start server in background
            self.server_process = subprocess.Popen(
                [server_exe],
                cwd=self.base_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait a moment and verify it started
            time.sleep(3)
            if self.server_process.poll() is None:
                self.log(f"✅ Server started successfully (PID: {self.server_process.pid})")
                return True
            else:
                self.log("❌ Server failed to start")
                return False
                
        except Exception as e:
            self.log(f"❌ Error starting server: {str(e)}")
            return False
    
    def stop_server(self):
        """Stop the FastAPI server"""
        if not self.server_process or self.server_process.poll() is not None:
            return
            
        try:
            self.log("🛑 Stopping server due to inactivity...")
            self.server_process.terminate()
            
            # Wait for graceful shutdown
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.log("⚠️  Force killing server...")
                self.server_process.kill()
                
            self.server_process = None
            self.log("✅ Server stopped")
            
        except Exception as e:
            self.log(f"❌ Error stopping server: {str(e)}")
    
    def setup_startup(self):
        """Add launcher to Windows startup"""
        try:
            import winreg
            
            # Path to this launcher executable
            launcher_path = os.path.join(self.base_dir, "SmartLauncher.exe")
            if not os.path.exists(launcher_path):
                self.log("⚠️  SmartLauncher.exe not found - startup registration skipped")
                return False
            
            # Add to Windows startup registry
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            winreg.SetValueEx(
                key,
                "SyncAnywhereService",
                0,
                winreg.REG_SZ,
                f'"{launcher_path}" --background'
            )
            
            winreg.CloseKey(key)
            self.log("✅ Added to Windows startup")
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to setup startup: {str(e)}")
            return False
    
    def remove_startup(self):
        """Remove launcher from Windows startup"""
        try:
            import winreg
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            try:
                winreg.DeleteValue(key, "SyncAnywhereService")
                self.log("✅ Removed from Windows startup")
            except FileNotFoundError:
                self.log("ℹ️  Not found in startup registry")
            
            winreg.CloseKey(key)
            return True
            
        except Exception as e:
            self.log(f"❌ Failed to remove startup: {str(e)}")
            return False
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.log("🚀 Smart Launcher started")
        self.log(f"📁 Working directory: {self.base_dir}")
        self.log(f"⏰ Idle timeout: {self.idle_timeout // 60} minutes")
        
        try:
            while True:
                # Check for activity
                has_connections = self.has_active_connections()
                port_in_use = self.is_port_in_use(self.port)
                
                if has_connections or port_in_use:
                    self.last_activity = datetime.now()
                    
                    # Start server if not running and port is not in use by something else
                    if not port_in_use:
                        self.start_server()
                
                # Check if we should stop due to inactivity
                idle_time = (datetime.now() - self.last_activity).total_seconds()
                
                if (self.server_process and 
                    self.server_process.poll() is None and 
                    idle_time > self.idle_timeout):
                    self.stop_server()
                
                # Sleep before next check  
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            self.log("🛑 Launcher stopped by user")
        except Exception as e:
            self.log(f"❌ Monitor error: {str(e)}")
        finally:
            if self.server_process:
                self.stop_server()
    
    def run_background(self):
        """Run in background mode (for startup)"""
        # Hide console window
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        
        self.monitor_loop()
    
    def show_status(self):
        """Show current status"""
        print("\n" + "="*50)
        print("🌟 SYNCANYWHERE SMART LAUNCHER STATUS")
        print("="*50)
        
        # Check server status
        if self.is_port_in_use(self.port):
            print("🟢 Server Status: RUNNING")
            
            # Get local IP
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    local_ip = s.getsockname()[0]
                print(f"🌐 Server URL: http://{local_ip}:8000")
            except:
                print("🌐 Server URL: http://localhost:8000")
        else:
            print("🔴 Server Status: STOPPED")
        
        # Check connections
        if self.has_active_connections():
            print("📱 Active Connections: YES")
        else:
            print("📱 Active Connections: NO")
        
        # Check startup status
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                winreg.QueryValueEx(key, "SyncAnywhereService")
                print("🚀 Windows Startup: ENABLED")
            except FileNotFoundError:
                print("🚀 Windows Startup: DISABLED")
            winreg.CloseKey(key)
        except:
            print("🚀 Windows Startup: UNKNOWN")
        
        print("="*50)

def main():
    launcher = SmartLauncher()
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "--background":
            launcher.run_background()
        elif command == "install":
            launcher.setup_startup()
            print("✅ Installed! SyncAnywhere will now start automatically with Windows.")
        elif command == "uninstall":
            launcher.remove_startup()
            print("✅ Uninstalled! SyncAnywhere will no longer start automatically.")
        elif command == "status":
            launcher.show_status()
        elif command == "start":
            if launcher.start_server():
                print("✅ Server started!")
            else:
                print("❌ Failed to start server")
        elif command == "stop":
            launcher.stop_server()
            print("✅ Server stopped!")
        else:
            print("Usage:")
            print("  SmartLauncher.exe install    - Enable auto-start with Windows")
            print("  SmartLauncher.exe uninstall  - Disable auto-start")
            print("  SmartLauncher.exe status     - Show current status")
            print("  SmartLauncher.exe start      - Start server manually")
            print("  SmartLauncher.exe stop       - Stop server manually")
    else:
        # Interactive mode
        launcher.show_status()
        print("\nPress Ctrl+C to exit or run with 'install' to enable auto-start")
        launcher.monitor_loop()

if __name__ == "__main__":
    main()