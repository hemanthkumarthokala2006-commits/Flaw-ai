from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import subprocess
import urllib.request
import urllib.parse
import re
import webbrowser

router = APIRouter(prefix="/api/system", tags=["System"])

class OpenAppRequest(BaseModel):
    app_name: str

class SendMessageRequest(BaseModel):
    person: str
    message: str

@router.post("/open")
async def open_app(request: OpenAppRequest):
    app_name = request.app_name.lower().strip()
    
    app_mapping = {
        "whatsapp": "whatsapp:",
        "what's up": "whatsapp:",
        "whats up": "whatsapp:",
        "calculator": "calc",
        "notepad": "notepad",
        "excel": "excel",
        "word": "winword",
        "powerpoint": "powerpnt",
        "chrome": "chrome",
        "edge": "msedge",
        "spotify": "spotify:",
        "telegram": "telegram:",
        "discord": "update",
        "settings": "ms-settings:",
        "camera": "microsoft.windows.camera:",
        "mail": "outlookmail:",
        "calendar": "outlookcal:",
        "weather": "bingweather:",
        "maps": "bingmaps:",
        "photos": "ms-photos:",
        "paint": "mspaint",
        "explorer": "explorer",
        "file explorer": "explorer",
        "cmd": "cmd",
        "command prompt": "cmd",
        "terminal": "wt",
        "vs code": "code",
        "visual studio code": "code",
        "task manager": "taskmgr",
        "control panel": "control",
        "netflix": "netflix:",
        "twitter": "twitter:",
    }
    
    if app_name in app_mapping:
        command = app_mapping[app_name]
        try:
            subprocess.Popen(f"start {command}", shell=True)
            return {"status": "success", "message": f"Opened {app_name}"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to open app: {str(e)}")
    else:
        try:
            # Try dynamic search for any installed Windows app
            ps_cmd = f"powershell -Command \"Get-StartApps | Where-Object {{$_.Name -match '{app_name}'}} | Select-Object -First 1 -ExpandProperty AppID\""
            result = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                command = result.stdout.strip()
                subprocess.Popen(f"explorer shell:AppsFolder\\{command}", shell=True)
                return {"status": "success", "message": f"Opened {app_name}"}
            else:
                raise HTTPException(status_code=404, detail="App not found locally")
        except Exception as e:
            raise HTTPException(status_code=404, detail="App not found locally")


@router.post("/play")
async def play_media(request: OpenAppRequest):
    query = request.app_name
    try:
        query_string = urllib.parse.urlencode({"search_query": query})
        url = "https://www.youtube.com/results?" + query_string
        
        html_content = urllib.request.urlopen(url)
        search_results = re.findall(r'watch\?v=(.{11})', html_content.read().decode())
        
        if search_results:
            video_url = f"https://www.youtube.com/watch?v={search_results[0]}"
            # Open directly in default browser
            webbrowser.open(video_url)
            return {"status": "success", "message": f"Playing {query} on YouTube"}
        else:
            raise HTTPException(status_code=404, detail="Video not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/message")
async def send_message(request: SendMessageRequest):
    try:
        # Pre-fill the message and person's name so it opens in WhatsApp Desktop
        text = urllib.parse.quote(f"Hey {request.person.title()}, {request.message}")
        uri = f"whatsapp://send?text={text}"
        webbrowser.open(uri)
        return {"status": "success", "message": f"Opening WhatsApp to message {request.person}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
