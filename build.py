import subprocess
import os

APP_NAME = "SyncService"
ENTRY_SCRIPT = "main.py"
DIST_PATH = "."  # Output in current folder

print("🛠️  Building .exe for SyncAnywhere...")

# Clean previous build (optional)
if os.path.exists("build"):
    subprocess.run(["rmdir", "/S", "/Q", "build"], shell=True)
if os.path.exists("__pycache__"):
    subprocess.run(["rmdir", "/S", "/Q", "__pycache__"], shell=True)
if os.path.exists("{}.spec".format(APP_NAME)):
    os.remove("{}.spec".format(APP_NAME))

# Run PyInstaller
subprocess.run([
    "pyinstaller",
    ENTRY_SCRIPT,
    "--onefile",
    "--name", APP_NAME,
    "--distpath", DIST_PATH,
    "--paths", "./app"
])

print("✅ Done! Check ./SyncService.exe")
