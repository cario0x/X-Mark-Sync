import sys
import os
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.main import SyncService
from src.config import ConfigManager

app = FastAPI()

# Setup templates
templates = Jinja2Templates(directory="src/web/templates")
# app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Global state for logs
logs = []
service = SyncService(logger=lambda msg: logs.append(msg))

def get_recent_bookmarks(limit=20):
    config_mgr = ConfigManager()
    base_dir = config_mgr.get("obsidian_vault_path")
    if not os.path.exists(base_dir):
        return []
    
    files = []
    for root, dirs, filenames in os.walk(base_dir):
        for filename in filenames:
            if filename.endswith(".md"):
                full_path = os.path.join(root, filename)
                files.append(full_path)
    
    # Sort by modification time
    files.sort(key=os.path.getmtime, reverse=True)
    recent_files = files[:limit]
    
    bookmarks = []
    for f in recent_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                content = file.read()
                # Simple parsing for demo
                title = os.path.basename(f).replace(".md", "")
                bookmarks.append({"title": title, "path": f})
        except:
            pass
    return bookmarks

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    bookmarks = get_recent_bookmarks()
    return templates.TemplateResponse("index.html", {"request": request, "bookmarks": bookmarks})

@app.post("/api/sync")
async def start_sync(background_tasks: BackgroundTasks):
    if service.is_running:
        return JSONResponse({"status": "running", "message": "Sync already running"})
    
    logs.clear()
    background_tasks.add_task(service.run_sync)
    return JSONResponse({"status": "started", "message": "Sync started in background"})

@app.get("/api/logs")
async def get_logs():
    return {"logs": logs, "is_running": service.is_running}

@app.get("/api/config")
async def get_config():
    cm = ConfigManager()
    return cm.config

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

