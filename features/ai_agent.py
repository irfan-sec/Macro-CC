import json
import base64
import config
from core.event_model import event_from_dict

SYSTEM_PROMPT = """You are an AI assistant that converts natural language commands into a list of macro events for Macro Recorder Pro.
Your goal is to output ONLY a valid JSON array of event dictionaries, with no markdown formatting or extra text.

Available event types (output as dicts in a JSON array):

1. KeyboardEvent (for typing text):
{
  "type": "key_press",
  "key": "H",
  "timestamp": 0.0
}
{
  "type": "key_release",
  "key": "H",
  "timestamp": 0.1
}
(For typing long text, you can output multiple key_press/key_release events, or use a key_combo).

2. SystemEvent (for launching apps, waiting, or shortcuts):
{
  "type": "run_app",
  "action": "run_app",
  "value": "notepad.exe",
  "comment": "Open Notepad",
  "timestamp": 0.0
}
{
  "type": "wait_seconds",
  "action": "wait_seconds",
  "value": "1.0",
  "comment": "Wait for app to load",
  "timestamp": 0.0
}
{
  "type": "key_combo",
  "action": "key_combo",
  "value": "ctrl+c",
  "comment": "Copy",
  "timestamp": 0.0
}
{
  "type": "key_combo",
  "action": "key_combo",
  "value": "enter",
  "comment": "Press Enter",
  "timestamp": 0.0
}

3. MouseEvent: (Prefer NOT to use mouse events unless specific coordinates are known, as screens vary. Use SystemEvent/KeyboardEvent instead when possible).

Example Command: "Open notepad and type Hello"
Example JSON Output:
[
  {"type": "run_app", "action": "run_app", "value": "notepad.exe", "comment": "Open Notepad", "timestamp": 0.0},
  {"type": "wait_seconds", "action": "wait_seconds", "value": "1.5", "comment": "Wait for Notepad", "timestamp": 0.0},
  {"type": "key_press", "key": "H", "timestamp": 0.0},
  {"type": "key_release", "key": "H", "timestamp": 0.0},
  {"type": "key_press", "key": "e", "timestamp": 0.0},
  {"type": "key_release", "key": "e", "timestamp": 0.0},
  {"type": "key_press", "key": "l", "timestamp": 0.0},
  {"type": "key_release", "key": "l", "timestamp": 0.0},
  {"type": "key_press", "key": "l", "timestamp": 0.0},
  {"type": "key_release", "key": "l", "timestamp": 0.0},
  {"type": "key_press", "key": "o", "timestamp": 0.0},
  {"type": "key_release", "key": "o", "timestamp": 0.0}
]

When asked to type text, you must break it down into individual key_press and key_release events for EACH character in the word. Do not combine them. Or, use a key_combo for a full string if supported by the player. Actually, the player might only support key_combo for things like "ctrl+c" or single keys like "enter". Always output valid JSON array ONLY.
"""

class AIAgent:
    def __init__(self):
        pass

    def generate_macro(self, command: str, provider: str = None, api_key: str = None, image_path: str = None) -> list:
        provider = provider or config.AI_PROVIDER
        key = api_key
        if not key:
            if provider == "gemini":
                key = config.GEMINI_API_KEY
            elif provider == "openai":
                key = config.OPENAI_API_KEY
            elif provider == "claude":
                key = config.CLAUDE_API_KEY
                
        if not key:
            raise ValueError(f"API Key for {provider} is not set.")

        try:
            if provider == "gemini":
                return self._call_gemini(command, key, image_path)
            elif provider == "openai":
                return self._call_openai(command, key, image_path)
            elif provider == "claude":
                return self._call_claude(command, key, image_path)
            else:
                raise ValueError(f"Unsupported AI provider: {provider}")
        except Exception as e:
            print(f"AI Generation Error: {e}")
            raise e

    def _call_gemini(self, command: str, api_key: str, image_path: str = None):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        
        # We use a standard text generation call, trying to enforce JSON output.
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        prompt = SYSTEM_PROMPT + "\n\nUser Command: " + command
        contents = [prompt]
        
        if image_path:
            import PIL.Image
            img = PIL.Image.open(image_path)
            contents.append(img)
            
        response = model.generate_content(contents)
        return self._parse_json(response.text)

    def _call_openai(self, command: str, api_key: str, image_path: str = None):
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        
        user_content = [{"type": "text", "text": command}]
        
        if image_path:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}"
                }
            })
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
        )
        return self._parse_json(response.choices[0].message.content)
        
    def _call_claude(self, command: str, api_key: str, image_path: str = None):
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        
        user_content = []
        if image_path:
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
                
            import mimetypes
            mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
            
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": mime_type,
                    "data": image_data,
                }
            })
            
        user_content.append({"type": "text", "text": command})
        
        message = client.messages.create(
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_content}
            ],
            model="claude-3-5-sonnet-20240620",
        )
        return self._parse_json(message.content[0].text)

    def _parse_json(self, text: str) -> list:
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        data = json.loads(text)
        
        if not isinstance(data, list):
            # If the model returned an object with a key holding the array, try to extract it
            for val in data.values():
                if isinstance(val, list):
                    data = val
                    break
                    
        events = []
        for d in data:
            events.append(event_from_dict(d))
            
        return events
