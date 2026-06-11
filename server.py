"""
AI Bot proxy server for Houses Game.
Loads OPENROUTER_API_KEY from env or ~/.hermes/.env.
Run: python server.py
"""
import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

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
    print("ERROR: OPENROUTER_API_KEY not found")
    sys.exit(1)

MODEL = "google/gemini-2.5-flash-lite"

SYSTEM_PROMPT = """You are an AI bot in a multiplayer arena shooter. Control your character tactically.

YOUR GOAL: Kill enemies. Survive.

RESPOND WITH VALID JSON ONLY:
{"dx": -1 to 1, "dy": -1 to 1, "shoot": true/false, "aim_angle": radians}

STRATEGY:
1. MOVE TOWARD nearest enemy unless low HP
2. When enemy < 300px: AIM at them (use their angleTo) and SHOOT
3. If HP < 4: RETREAT (move AWAY from nearest: dx=-cos(angleTo), dy=-sin(angleTo))
4. If enemy < 150px: SHOOT and STRAFE (dx=-sin(angleTo), dy=cos(angleTo))
5. Target LOWEST HP enemy when multiple are close
6. NEVER stand still
7. Use houses for cover when retreating

You have: your position, HP, enemies with distances and angles, nearby houses.
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
            self.send_error(404); return
        length = int(self.headers.get("Content-Length", 0))
        state = json.loads(self.rfile.read(length))
        payload = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Game state:\n{json.dumps(state, indent=2)}\n\nJSON action:"}
            ],
            "temperature": 0.5, "max_tokens": 200,
            "response_format": {"type": "json_object"}
        }).encode()
        req = Request("https://openrouter.ai/api/v1/chat/completions", data=payload, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8765",
            "X-Title": "Houses Game Bot"
        })
        try:
            resp = urlopen(req, timeout=15)
            data = json.loads(resp.read())
            action = json.loads(data["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"API error: {e}")
            import random, math
            a = random.random() * math.pi * 2
            action = {"dx": math.cos(a)*0.5, "dy": math.sin(a)*0.5, "shoot": random.random()<0.3, "aim_angle": a}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(action).encode())

    def log_message(self, fmt, *args):
        print(f"[server] {args[0]}")

if __name__ == "__main__":
    port = 8765
    print(f"Bot server on http://localhost:{port} | Model: {MODEL}")
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
