from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import subprocess
import urllib.request
import urllib.parse
import re
import webbrowser

from app.services.gemini import get_gemini_response, get_intent

router = APIRouter(prefix="/api/system", tags=["System"])

class ProcessRequest(BaseModel):
    query: str

@router.post("/process")
async def process_command(request: ProcessRequest):
    try:
        result = await get_intent(request.query)
        intent = result.get("intent")
        params = result.get("params", {})
        
        return {
            "status": "success",
            "intent": intent,
            "params": params
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/screenshot")
async def take_screenshot():
    try:
        import mss
        import os
        import uuid
        from app.config import settings
        
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_id = uuid.uuid4().hex
        filename = f"screenshot_{file_id}.png"
        file_path = os.path.join(settings.UPLOAD_DIR, filename)
        
        with mss.mss() as sct:
            sct.shot(output=file_path)
            
        return {
            "status": "success",
            "media_url": f"{settings.BACKEND_URL}/uploads/{filename}",
            "file_path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class OpenAppRequest(BaseModel):
    app_name: str

class SendMessageRequest(BaseModel):
    person: str
    message: str
    is_image: bool = False

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

        if request.is_image:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_path = filedialog.askopenfilename(
                title="Select Image to Send",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
            )
            root.destroy()
            if file_path:
                subprocess.run(f'powershell -command "Set-Clipboard -Path \'{file_path}\'"', shell=True)
            else:
                return {"status": "success", "message": "Image sending cancelled."}

        use_web = False

        if app_name in ["telegram", "tg"]:
            subprocess.Popen("start telegram:", shell=True)
            if not wait_for_app_focus():
                use_web = True
            else:
                time.sleep(1)
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(1)
                pyautogui.write(person)
                time.sleep(2)
                pyautogui.press('enter')
                time.sleep(1)
                if request.is_image:
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(1)
                else:
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
                use_web = True
            else:
                time.sleep(1)
                pyautogui.hotkey('ctrl', 'k')
                time.sleep(1)
                pyautogui.write(person)
                time.sleep(2)
                pyautogui.press('enter')
                time.sleep(1)
                if request.is_image:
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(1)
                else:
                    pyautogui.write(message)
                time.sleep(0.5)
                pyautogui.press('enter')

        elif app_name in ["instagram", "ig", "insta"]:
            ps_cmd = "powershell -Command \"Get-StartApps | Where-Object {$_.Name -match 'instagram'} | Select-Object -First 1 -ExpandProperty AppID\""
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            if res.stdout.strip():
                subprocess.Popen(f"explorer shell:AppsFolder\\{res.stdout.strip()}", shell=True)
                if not wait_for_app_focus(10):
                    use_web = True
                else:
                    time.sleep(2)
                    # No reliable shortcut for Instagram desktop search
            else:
                use_web = True
                
            if use_web:
                import webbrowser
                webbrowser.open("https://www.instagram.com/direct/new/")
                time.sleep(6)
                pyautogui.write(person)
                time.sleep(3)
                pyautogui.press('tab')
                time.sleep(0.5)
                pyautogui.press('space') # Check the user
                time.sleep(0.5)
                # It's hard to reliably hit "Chat" button via tabs.
                # So we just leave it here for user.
                use_web = False # Handled

        elif app_name in ["snapchat", "snap"]:
            ps_cmd = "powershell -Command \"Get-StartApps | Where-Object {$_.Name -match 'snapchat'} | Select-Object -First 1 -ExpandProperty AppID\""
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            if res.stdout.strip():
                subprocess.Popen(f"explorer shell:AppsFolder\\{res.stdout.strip()}", shell=True)
                if not wait_for_app_focus(10):
                    use_web = True
                else:
                    time.sleep(2)
            else:
                use_web = True
                
            if use_web:
                import webbrowser
                webbrowser.open("https://web.snapchat.com/")
                time.sleep(6)
                use_web = False # Handled

        elif app_name == "whatsapp":
            subprocess.Popen("start whatsapp:", shell=True)
            if not wait_for_app_focus():
                use_web = True
            else:
                time.sleep(1) 
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(1)
                pyautogui.write(person)
                time.sleep(2) 
                pyautogui.press('enter')
                time.sleep(1)
                if request.is_image:
                    pyautogui.hotkey('ctrl', 'v')
                    time.sleep(1)
                else:
                    if message == "Hello":
                        pyautogui.write(f"Hey {person.title()}, hi")
                    else:
                        pyautogui.write(message.capitalize())
                time.sleep(0.5)
                pyautogui.press('enter')

        else:
            # Dynamically search for ANY other specified chatting application
            ps_cmd = f"powershell -Command \"Get-StartApps | Where-Object {{$_.Name -match '{app_name}'}} | Select-Object -First 1 -ExpandProperty AppID\""
            res = subprocess.run(ps_cmd, shell=True, capture_output=True, text=True)
            if res.stdout.strip():
                subprocess.Popen(f"explorer shell:AppsFolder\\{res.stdout.strip()}", shell=True)
                if not wait_for_app_focus(15):
                    use_web = True
                else:
                    time.sleep(2)
                    # Try common shortcut: Ctrl+F for search
                    pyautogui.hotkey('ctrl', 'f')
                    time.sleep(1)
                    pyautogui.write(person)
                    time.sleep(2)
                    pyautogui.press('enter')
                    time.sleep(1)
                    if request.is_image:
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(1)
                    else:
                        if message == "Hello":
                            pyautogui.write(f"Hey {person.title()}, hi")
                        else:
                            pyautogui.write(message.capitalize())
                    time.sleep(0.5)
                    pyautogui.press('enter')
            else:
                use_web = True

        if use_web and app_name not in ["instagram", "ig", "insta", "snapchat", "snap"]:
            import webbrowser
            import urllib.parse
            if app_name == "whatsapp":
                text = urllib.parse.quote(f"Hey {person.title()}, {message}" if not request.is_image else "")
                webbrowser.open(f"https://api.whatsapp.com/send?text={text}")
            elif app_name in ["telegram", "tg"]:
                webbrowser.open("https://web.telegram.org/")
            elif app_name == "discord":
                webbrowser.open("https://discord.com/app")
            else:
                # Open google search for the requested chatting app
                webbrowser.open(f"https://www.google.com/search?q={urllib.parse.quote(app_name)}+web")

        return {"status": "success", "message": f"Successfully processed message to {person} on {app_name.title()}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class AskRequest(BaseModel):
    query: str
    media_url: str | None = None

@router.post("/ask")
async def ask_agent(request: AskRequest):
    try:
        from app.services.gemini import get_gemini_response
        class DummyMsg:
            def __init__(self, role, content):
                self.role = role
                self.content = content
        
        system_msg = DummyMsg("user", "You are Flaw, an AI assistant created by Hemanth kumar. Please provide a short, conversational voice answer. No markdown.")
        user_msg = DummyMsg("user", request.query)
        
        image_path = None
        if request.media_url:
            filename = request.media_url.split("/")[-1]
            image_path = os.path.join(settings.UPLOAD_DIR, filename)
            
        response = await get_gemini_response([system_msg, user_msg], image_path=image_path)
        response = response.replace("*", "").replace("#", "")
        return {"status": "success", "answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
