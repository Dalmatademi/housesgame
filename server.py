"""
AI Bot proxy server for Houses Game.
Run: python server.py
"""
import json, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

def load_key():
    k = os.environ.get("OPENROUTER_API_KEY", "")
    if k:
        return k
    p = os.path.expanduser("~/.hermes/.env")
    if not os.path.exists(p):
        return ""
    E = chr(61)
    Q = chr(34)
    S = chr(39)
    pre = "OPENROUTER_API_KEY"
    with open(p) as f:
        for line in f:
            line = line.strip()
            if line.startswith(pre + E):
                return line.split(E, 1)[1].strip().strip(Q).strip(S)
    return ""

KEY = load_key()
if not KEY:
    print("ERROR: OPENROUTER_API_KEY not found")
    sys.exit(1)

MODEL = "google/gemini-2.5-flash-lite"
SP = """You are an AI bot in a multiplayer arena shooter. Control your character tactically.

YOUR GOAL: Kill enemies. Survive. Be aggressive.

RESPOND WITH VALID JSON ONLY:
{"dx": -1 to 1, "dy": -1 to 1, "shoot": true/false, "aim_angle": radians}

STRATEGY (follow strictly):
1. MOVE TOWARD nearest enemy unless HP < 4
2. Enemy < 300px away: AIM at them (use nearestEnemy.angleTo) + SHOOT
3. HP < 4: RETREAT - move AWAY from nearest enemy
4. Enemy < 150px: STRAFE sideways while shooting
5. Target LOWEST HP enemy when multiple are close
6. NEVER stand still
7. Use houses_nearby for cover when retreating

State includes: position, HP, enemies with pre-calculated distances and angles.
"""

class H(BaseHTTPRequestHandler):
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
        n = int(self.headers.get("Content-Length", 0))
        s = json.loads(self.rfile.read(n))
        p = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SP},
                {"role": "user", "content": "Game state:\n" + json.dumps(s, indent=2) + "\n\nJSON action:"}
            ],
            "temperature": 0.5, "max_tokens": 200,
            "response_format": {"type": "json_object"}
        }).encode()
        r = Request("https://openrouter.ai/api/v1/chat/completions", data=p, headers={
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8765",
            "X-Title": "Houses Game Bot"
        })
        try:
            resp = urlopen(r, timeout=15)
            d = json.loads(resp.read())
            a = json.loads(d["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"API err: {e}")
            import random, math
            ang = random.random() * math.pi * 2
            a = {"dx": math.cos(ang)*0.5, "dy": math.sin(ang)*0.5, "shoot": random.random()<0.3, "aim_angle": ang}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(a).encode())
    def log_message(self, f, *a):
        print(f"[srv] {a[0]}")

if __name__ == "__main__":
    print(f"Bot server http://localhost:8765 | {MODEL}")
    HTTPServer(("127.0.0.1", 8765), H).serve_forever()
