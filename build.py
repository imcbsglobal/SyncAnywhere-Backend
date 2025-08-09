# build.py
import subprocess
import os
import shutil

DIST_PATH = "."  # Output the EXE in current folder
CONFIG_FILE = "config.json"

APPS = [
    {
        "name": "SyncAnywhere",
        "entry": "start_server.py"
    },
    {
        "name": "SyncService",
        "entry": "run_service.py"
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
    subprocess.run([
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
    ])
    print(f"✅ Done: ./{app['name']}.exe")

print("\n🎉 Build process finished.")
print("\n📋 Next steps:")
print("1. Test both EXEs on the target machine")
print("2. Make sure config.json is in the same folder")
print("3. Check that Windows Firewall allows the apps")
print("4. Verify SQL Anywhere DSN is configured correctly")