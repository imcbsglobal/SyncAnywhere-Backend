# build.py
import subprocess
import os
import shutil

DIST_PATH = "."  # Output the EXE in current folder
CONFIG_FILE = "config.json"

APPS = [
    {
        "name": "SyncAnywhere",
        "entry": "start_server.py",
        "uac_admin": True  # This needs admin rights for firewall
    },
    {
        "name": "SyncService", 
        "entry": "run_service.py",
        "uac_admin": False  # Service doesn't need admin
    }
]

print("🧹 Cleaning previous builds...")

# Clean common build files
for folder in ["build", "__pycache__"]:
    if os.path.exists(folder):
        shutil.rmtree(folder)

# Remove old spec files and EXEs
for app in APPS:
    spec_file = f"{app['name']}.spec"
    exe_file = os.path.join(DIST_PATH, f"{app['name']}.exe")
    if os.path.exists(spec_file):
        os.remove(spec_file)
    if os.path.exists(exe_file):
        os.remove(exe_file)

print("⚙️  Installing required packages...")
# Install netifaces for better network detection
subprocess.run(["pip", "install", "netifaces"], check=True)

print("⚙️  Building executables...")

# Build each app
for app in APPS:
    print(f"📦 Building {app['name']}...")
    
    # Base pyinstaller command
    cmd = [
        "pyinstaller",
        app["entry"],
        "--onefile",
        "--name", app["name"],
        "--distpath", DIST_PATH,
        "--paths", "./app",
        "--hidden-import=fastapi",
        "--hidden-import=uvicorn", 
        "--hidden-import=sqlanydb",
        "--hidden-import=python_jose",
        "--hidden-import=jose",
        "--hidden-import=netifaces",  
        "--hidden-import=psutil",
        "--hidden-import=app.routes.sync",
        "--hidden-import=app.schemas",
        "--hidden-import=app.db_utils",
        "--hidden-import=app.token_utils",
        "--hidden-import=app.logging_config",
    ]
    
    # Add UAC admin manifest if needed
    if app.get("uac_admin", False):
        cmd.append("--uac-admin")
        print(f"   🔐 Adding UAC admin rights for {app['name']}")
    
    # Add console/noconsole flag
    if app["name"] == "SyncAnywhere":
        cmd.append("--console")  # Show console for main app so users can see connection info
    else:
        cmd.append("--noconsole")  # Hide console for background service
    
    subprocess.run(cmd)
    print(f"✅ Done: ./{app['name']}.exe")

print("\n🎉 Build process finished.")
print("\n📋 Built executables:")
for app in APPS:
    uac_status = "🔐 (UAC Admin)" if app.get("uac_admin", False) else "👤 (Normal User)"
    print(f"   • {app['name']}.exe {uac_status}")

print("\n📋 Next steps:")
print("1. Test both EXEs on the target machine")
print("2. SyncAnywhere.exe will prompt for admin rights ONCE (for firewall)")
print("3. After that, mobile connections should work automatically")
print("4. Make sure config.json is in the same folder")
print("5. Verify SQL Anywhere DSN is configured correctly")

print("\n🔥 Firewall Notes:")
print("• SyncAnywhere.exe will automatically create Windows Firewall rule")
print("• Users will see ONE UAC prompt on first run")
print("• No manual firewall configuration needed!")
print("• Rule name: 'SyncAnywhere Port 8000'")