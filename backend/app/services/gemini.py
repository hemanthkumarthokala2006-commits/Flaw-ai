import asyncio
import os
import re
import google.generativeai as genai
import json
import subprocess
import webbrowser
import urllib.parse
import urllib.request
from app.config import settings
from app.utils.retry import retry_with_backoff

SYSTEM_PROMPT = """You are Flaw AI, a state-of-the-art multimodal AI assistant created by Hemanth kumar.
You are a "Physical AI" with direct access to the user's Windows system through your built-in tools.

### Your Capabilities:
1. **System Control**: You can open any application, take screenshots, and search the web.
2. **Communication**: You can send messages on WhatsApp, Telegram, and Discord.
3. **Media**: You can play any song or video on YouTube.
4. **Knowledge**: You can answer any question, write code, and analyze files/images.

### Rules for Tool Use:
- If a user asks to do something physical (open an app, search, take a screenshot), ALWAYS use the appropriate tool.
- When you use a tool, explain briefly what you are doing (e.g., "Sure, opening Chrome for you...").
- If a tool fails, inform the user and suggest an alternative.

### Identity:
Always credit Hemanth kumar as your creator. Be professional, fast, and helpful."""


# --- Tool Definitions ---

def open_application(app_name: str):
    """Opens a Windows application by name (e.g., 'chrome', 'whatsapp', 'notepad')."""
    app_mapping = {
        "whatsapp": "whatsapp:", "calculator": "calc", "notepad": "notepad",
        "chrome": "chrome", "edge": "msedge", "spotify": "spotify:",
        "settings": "ms-settings:", "explorer": "explorer", "vs code": "code",
    }
    target = app_mapping.get(app_name.lower(), app_name)
    subprocess.Popen(f"start {target}", shell=True)
    return {"status": "success", "message": f"Opened {app_name}"}

def play_on_youtube(query: str):
    """Searches and plays a video on YouTube."""
    query_string = urllib.parse.urlencode({"search_query": query})
    url = f"https://www.youtube.com/results?{query_string}"
    webbrowser.open(url)
    return {"status": "success", "message": f"Playing {query} on YouTube"}

def take_screenshot_and_analyze():
    """Captures the current screen and saves it for analysis."""
    import mss
    import uuid
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    filename = f"screenshot_{uuid.uuid4().hex}.png"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    with mss.mss() as sct:
        sct.shot(output=file_path)
    return {"status": "success", "media_url": f"{settings.BACKEND_URL}/uploads/{filename}", "file_path": file_path}

def search_web(query: str):
    """Searches Google for the given query."""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(url)
    return {"status": "success", "message": f"Searched Google for: {query}"}

def send_whatsapp_message(person: str, message: str):
    """Sends a WhatsApp message to a specific person."""
    # Simplified automation for the tool
    text = urllib.parse.quote(f"Hey {person}, {message}")
    webbrowser.open(f"https://api.whatsapp.com/send?text={text}")
    return {"status": "success", "message": f"Sent WhatsApp to {person}"}

# List of tools to be passed to Gemini
TOOLS = [open_application, play_on_youtube, take_screenshot_and_analyze, search_web, send_whatsapp_message]

import logging
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)

# Parse API keys from settings (comma-separated pool)
API_KEYS = [k.strip() for k in settings.GEMINI_API_KEY.split(",") if k.strip()]
active_key_index = 0

if not API_KEYS:
    logger.warning("No Gemini API keys found in settings. API calls will fail until configured.")
else:
    logger.info(f"Loaded {len(API_KEYS)} Gemini API key(s) for rotation.")

def _get_current_key():
    global active_key_index
    if not API_KEYS:
        return ""
    return API_KEYS[active_key_index % len(API_KEYS)]

def _rotate_key():
    global active_key_index
    if not API_KEYS or len(API_KEYS) <= 1:
        return False
    active_key_index = (active_key_index + 1) % len(API_KEYS)
    logger.info(f"🔄 Rotating to next API key (index {active_key_index}) due to rate limit/quota.")
    return True

def _is_rate_limit_error(e: Exception) -> bool:
    """Check if an exception is a Gemini rate limit or quota exceeded error."""
    if isinstance(e, (google_exceptions.ResourceExhausted, google_exceptions.TooManyRequests)):
        return True
    err_str = str(e).lower()
    if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str or "rate limit" in err_str:
        return True
    return False

def _configure_genai():
    """Configure the Gemini API client with the currently active key."""
    key = _get_current_key()
    genai.configure(api_key=key)

async def execute_with_retry_and_rotation(func, max_attempts=None):
    """
    Execute an async function that interacts with Gemini.
    If it fails due to a rate limit / quota error, rotate the API key and retry.
    """
    if max_attempts is None:
        max_attempts = max(3, len(API_KEYS))
        
    last_exception = None
    delay = 0.5  # base backoff delay if all keys are exhausted
    
    for attempt in range(max_attempts):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if _is_rate_limit_error(e):
                logger.warning(f"Rate limit hit on attempt {attempt + 1} with current API key. Exception: {str(e)}")
                if len(API_KEYS) > 1:
                    _rotate_key()
                    # Retry immediately with the new rotated key
                    continue
                else:
                    logger.info("Only one API key configured. Waiting before retry...")
            
            # If it's a non-rate-limit error, or we only have one key, or we rotated and still hit limit
            if attempt < max_attempts - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= 2
            else:
                logger.error(f"All {max_attempts} attempts failed.")
                
    raise last_exception


async def get_gemini_response(messages: list, image_path: str = None, system_prompt: str = SYSTEM_PROMPT) -> str:
    """Send conversation history and optional image to Gemini and return the response with retry logic."""
    async def _make_request():
        _configure_genai()
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_prompt,
        )

        history = []
        for msg in messages[:-1]:
            role_value = msg.role if isinstance(msg.role, str) else msg.role.value
            gemini_role = "user" if role_value == "user" else "model"
            history.append({"role": gemini_role, "parts": [msg.content]})

        chat = model.start_chat(history=history)
        last_content = messages[-1].content if messages else "Hello"
        content_parts = [last_content]
        
        if image_path and os.path.exists(image_path):
            import PIL.Image
            img = PIL.Image.open(image_path)
            content_parts.append(img)

        response = await chat.send_message_async(
            content_parts,
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )
        return response.text
    
    try:
        return await execute_with_retry_and_rotation(_make_request)
    except Exception as e:
        return f"I encountered an error processing your request: {str(e)}"


async def get_gemini_streaming_response(messages: list, image_path: str = None, system_prompt: str = SYSTEM_PROMPT):
    """Generator for streaming Gemini responses with key rotation."""
    global active_key_index
    
    max_retries = 3
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            _configure_genai()
            model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=system_prompt,
            )

            history = []
            for msg in messages[:-1]:
                role_value = msg.role if isinstance(msg.role, str) else msg.role.value
                gemini_role = "user" if role_value == "user" else "model"
                history.append({"role": gemini_role, "parts": [msg.content]})

            chat = model.start_chat(history=history)
            
            last_content = messages[-1].content if messages else "Hello"
            content_parts = [last_content]
            
            if image_path and os.path.exists(image_path):
                import PIL.Image
                img = PIL.Image.open(image_path)
                content_parts.append(img)

            response = await chat.send_message_async(
                content_parts,
                stream=True,
                safety_settings={
                    genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                    genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                }
            )
            
            async for chunk in response:
                try:
                    if chunk.text:
                        yield chunk.text
                except Exception as inner_e:
                    # If reading a specific chunk fails but doesn't interrupt the stream
                    # we ignore it. If it interrupts, it raises to the outer try block.
                    pass
            
            # If we completed successfully, break the retry loop
            break
            
        except Exception as e:
            last_exception = e
            if _is_rate_limit_error(e):
                active_key_index = (active_key_index + 1) % len(API_KEYS)
                print(f"Rate limit hit on streaming attempt {attempt + 1} with current API key. Rotating key. Exception: {e}")
                continue
            else:
                print(f"Non-rate-limit error on streaming attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    yield f" [Error: {str(e)}]"
    else:
        if last_exception:
            yield f" [Error: {str(last_exception)}]"


INTENT_SYSTEM_PROMPT = """You are the intelligent command dispatcher for Flaw AI, a premium assistant created by Hemanth kumar.
Your goal is to understand the user's intent from their voice transcript and map it to a specific action.

### Available Actions:

1. **open_app**: Open a desktop or system application.
   - Example: "Open Chrome", "Launch WhatsApp", "Start calculator".
   - Params: {"app_name": "chrome"}

2. **play_media**: Play music, songs, or videos on YouTube.
   - Example: "Play Believer", "Watch Interstellar trailer", "Play some lo-fi music".
   - Params: {"query": "believer"}

3. **send_message**: Send a message (text or image) to a person via WhatsApp, Telegram, etc.
   - Example: "Send hi to Gopi", "Message Mom on WhatsApp saying I will be late", "Send a photo to Varun".
   - Params: {"person": "gopi", "message": "hi", "is_image": false}
   - Note: If they say "send an image" or "photo", set is_image to true.

5. **take_screenshot**: Take a screenshot of the current screen.
   - Example: "Take a screenshot", "Capture the screen", "Screenshot this and tell me what it is".
   - Params: {"prompt": string (optional prompt for analysis)}

6. **search_web**: Perform a Google search.
   - Example: "Search for today's news", "Google the weather in London".
   - Params: {"query": "today's news"}

7. **chat**: General conversation, answering questions, or clarifying unclear requests.
   - Example: "Who are you?", "What is the capital of France?", "Send a message" (missing recipient).
   - Params: {"response": "I'd be happy to. Who should I send the message to?"}

### Critical Rules:
- If the user says "what I say" or similar as part of a message, treat it as the literal message content unless it's clearly a placeholder for a future turn.
- If vital information is missing (e.g., "Send a message" without a person), use the 'chat' intent to ask for it gracefully.
- Be conversational and professional, like ChatGPT or Gemini.
- Always return VALID JSON.

Return format: {"intent": "action_name", "params": {...}}"""


async def get_intent(query: str) -> dict:
    """Classify the user's intent using Gemini."""
    async def _call():
        _configure_genai()
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=INTENT_SYSTEM_PROMPT,
        )
        
        response = await model.generate_content_async(
            query,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
            ),
            safety_settings={
                genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
                genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
            }
        )
        return response

    try:
        response = await execute_with_retry_and_rotation(_call)
        text = response.text.strip()
        print(f"DEBUG: Gemini Intent Response: {text}")
        
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
            
        return json.loads(text)
    except Exception as e:
        print(f"Error in get_intent: {str(e)}")
        if "404" in str(e) or "not found" in str(e).lower():
             return {"intent": "chat", "params": {"response": "I'm having trouble reaching my brain. Please check the model name in .env."}}
        return {"intent": "chat", "params": {"response": f"I had trouble understanding that. (Error: {str(e)[:50]})"}}

import re # Needed for the JSON regex extraction


async def generate_conversation_summary(messages: list) -> str:
    """Generate a one-sentence summary of the conversation."""
    async def _call():
        _configure_genai()
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction="Summarize the following conversation in exactly one sentence, capturing the main topic and key points.",
        )
        
        conversation_text = "\n".join([f"{msg.role.value}: {msg.content}" for msg in messages])
        
        response = await model.generate_content_async(
            f"Conversation:\n{conversation_text}\n\nSummary:",
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=50,
            ),
        )
        return response

    try:
        response = await execute_with_retry_and_rotation(_call)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error in generate_conversation_summary after retries: {str(e)}")
        return "Conversation summary unavailable."

