"""
AI Bot proxy server for Houses Game.
Proxies bot think requests to OpenRouter (qwen/qwen3-coder:free).
Loads OPENROUTER_API_KEY from environment or ~/.hermes/.env.
Run: python server.py
"""
import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

# Load API key
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
if not API_KEY:
    env_path = os.path.expanduser("~/.hermes/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENROUTER_API_KEY="):
                    API_KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found in env or ~/.hermes/.env")
    sys.exit(1)

MODEL = "qwen/qwen3-coder:free"

SYSTEM_PROMPT = """You control a bot in a multiplayer arena game. You receive game state and must respond with a JSON action.

RESPOND ONLY WITH VALID JSON. No explanation, no markdown, just the JSON object.

The world is 2D. Available actions:
- Move: set dx, dy (floats -1 to 1, they'll be normalized)
- Shoot: set shoot=true, aim_angle in radians (0=right, pi/2=down, etc)
- Idle: dx=0, dy=0, shoot=false

Be strategic: move toward enemies, dodge when low HP, shoot when aligned.
Do NOT stay still forever. Be aggressive but smart.
"""

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/think":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        state = json.loads(body)

        user_prompt = json.dumps(state, indent=2)
        full_prompt = f"Game state:\n{user_prompt}\n\nRespond with your action JSON:"

        payload = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": full_prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 150,
            "response_format": {"type": "json_object"}
        }).encode()

        req = Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:8765",
                "X-Title": "Houses Game Bot"
            }
        )

        try:
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            action = json.loads(content)
        except (URLError, json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"API error: {e}")
            import random, math
            angle = random.random() * math.pi * 2
            action = {"dx": math.cos(angle)*0.5, "dy": math.sin(angle)*0.5, "shoot": random.random()<0.3, "aim_angle": angle}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(action).encode())

    def log_message(self, format, *args):
        print(f"[server] {args[0]}")

if __name__ == "__main__":
    port = 8765
    print(f"Bot proxy server on http://localhost:{port}")
    print(f"Model: {MODEL}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
