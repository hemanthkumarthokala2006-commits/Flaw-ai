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
        import pyautogui
        import time
        import subprocess
        
        person = request.person.lower().strip()
        message = request.message.strip()
        app_name = "whatsapp" # default
        
        # Check if the app is specified in the person's name (e.g., "gopi on telegram")
        if " on " in person:
            parts = person.split(" on ")
            person = parts[0].strip()
            app_name = parts[-1].strip()
            
        # Check if the app is specified in the message (e.g., "hi on discord")
        if " on " in message.lower():
            parts = message.rsplit(" on ", 1)
            message = parts[0].strip()
            app_name = parts[1].strip()

        # Fix parsing if message is stuck inside person name (e.g. "gopi varun hi")
        if message == "Hello": # Frontend default
            common_starts = [" hi ", " hello ", " hey ", " what ", " how ", " saying "]
            for start in common_starts:
                if start in person:
                    parts = person.split(start, 1)
                    person = parts[0].strip()
                    message = start.strip() + " " + parts[1].strip()
                    break

        def wait_for_app_focus(timeout=10):
            # UWP apps like WhatsApp often don't report their window titles correctly to pyautogui.
            # Instead of looking for "WhatsApp", we wait until the web browser (Chrome/Edge) LOSES focus.
            # When the browser loses focus, it means the new app has successfully popped up.
            for _ in range(timeout):
                time.sleep(1)
                title = pyautogui.getActiveWindowTitle()
                if title:
                    title = title.lower()
                    if "chrome" not in title and "edge" not in title and "firefox" not in title and "brave" not in title:
                        return True
                else:
                    # If title is empty, it might be a UWP app like WhatsApp that successfully took focus
                    return True
            return False

        if app_name in ["telegram", "tg"]:
            subprocess.Popen("start telegram:", shell=True)
            if not wait_for_app_focus():
                raise Exception("Telegram Desktop did not open. Is it installed?")
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1)
            pyautogui.write(person)
            time.sleep(2)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.write(message)
            time.sleep(0.5)
            pyautogui.press('enter')
            
        elif app_name in ["discord"]:
            ps_cmd = "powershell -Command \"Get-StartApps | Where-Object {$_.Name -match 'discord'} | Select-Object -First 1 -ExpandProperty AppID\""
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            if res.stdout.strip():
                subprocess.Popen(f"explorer shell:AppsFolder\\{res.stdout.strip()}", shell=True)
            else:
                subprocess.Popen("start discord:", shell=True)
                
            if not wait_for_app_focus(15):
                raise Exception("Discord did not open. Is it installed?")
            time.sleep(1)
            pyautogui.hotkey('ctrl', 'k')
            time.sleep(1)
            pyautogui.write(person)
            time.sleep(2)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.write(message)
            time.sleep(0.5)
            pyautogui.press('enter')
            
        else:
            # Default to WhatsApp
            app_name = "whatsapp"
            subprocess.Popen("start whatsapp:", shell=True)
            if not wait_for_app_focus():
                raise Exception("WhatsApp Desktop did not open. Is it installed?")
            time.sleep(1) 
            pyautogui.hotkey('ctrl', 'f')
            time.sleep(1)
            pyautogui.write(person)
            time.sleep(2) 
            pyautogui.press('enter')
            time.sleep(1)
            if message == "Hello":
                pyautogui.write(f"Hey {person.title()}, hi")
            else:
                pyautogui.write(message.capitalize())
            time.sleep(0.5)
            pyautogui.press('enter')
        
        return {"status": "success", "message": f"Successfully sent message to {person} on {app_name.title()}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AskRequest(BaseModel):
    query: str

@router.post("/ask")
async def ask_agent(request: AskRequest):
    try:
        from app.services.gemini import get_gemini_response
        class DummyMsg:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        # Create a tiny prompt context asking for concise voice answers
        system_msg = DummyMsg("user", "Please provide a very short, concise, conversational answer suitable for a voice assistant. No markdown or formatting.")
        user_msg = DummyMsg("user", request.query)
        
        response = await get_gemini_response([system_msg, user_msg])
        # Clean up any asterisks or markdown that might sound weird in text-to-speech
        response = response.replace("*", "").replace("#", "")
        return {"status": "success", "answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
