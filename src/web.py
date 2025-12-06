from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import sys
import subprocess

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import SyncService
from src.config import ConfigManager

app = FastAPI(title="X-Mark Sync Web")

# Setup templates
base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, "templates")
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

service = SyncService()

class PathUpdate(BaseModel):
    path: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    config_mgr = ConfigManager()
    current_path = config_mgr.get("obsidian_vault_path")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_path": current_path
    })

@app.post("/api/start_monitor")
async def start_monitor():
    if not service.is_running:
        service.start(monitor=True)
        return {"status": "started", "mode": "monitoring"}
    return {"status": "error", "message": "Already running"}

@app.post("/api/import_now")
async def import_now():
    if not service.is_running:
        service.start(monitor=False)
        return {"status": "started", "mode": "one-time"}
    return {"status": "error", "message": "Already running"}

@app.post("/api/stop")
async def stop_sync():
    service.stop()
    return {"status": "stopping"}

@app.get("/api/status")
async def get_status():
    return {
        "is_running": service.is_running,
        "is_monitoring": service.is_monitoring,
        "logs": service.get_logs()
    }

@app.get("/api/select_folder")
def select_folder():
    """
    Opens a native folder selection dialog on the server side (local machine).
    Running as synchronous 'def' to avoid blocking the asyncio event loop during
    the modal dialog wait time.
    """
    if sys.platform == "darwin":
        try:
            # AppleScript to prompt for folder, trying to be frontmost
            script = '''
            try
                tell application "System Events"
                    activate
                    set f to choose folder with prompt "Select Obsidian Vault Folder"
                    return POSIX path of f
                end tell
            on error
                return ""
            end try
            '''
            result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
            if result.returncode == 0:
                folder_path = result.stdout.strip()
                if folder_path:
                    config_mgr = ConfigManager()
                    config_mgr.set("obsidian_vault_path", folder_path)
                    return {"status": "success", "path": folder_path}
        except Exception as e:
            print(f"AppleScript error: {e}")
            pass
    else:
        # Fallback to Tkinter for Windows/Linux
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            folder_path = filedialog.askdirectory(title="Select Obsidian Vault Folder")
            root.destroy()
            if folder_path:
                config_mgr = ConfigManager()
                config_mgr.set("obsidian_vault_path", folder_path)
                return {"status": "success", "path": folder_path}
        except Exception:
            pass

    return {"status": "cancelled"}

@app.get("/api/get_config")
async def get_config():
    config_mgr = ConfigManager()
    return {"obsidian_vault_path": config_mgr.get("obsidian_vault_path")}

def run_server():
    print("Starting Web Server at http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == "__main__":
    run_server()
