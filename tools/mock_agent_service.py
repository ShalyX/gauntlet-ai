"""Mock Agent HTTP service for testing and demoing GauntletAI challenges."""

import http.server
import json
import sys

PORT = 8088
MODE = "aligned"  # "aligned" or "vulnerable"


class AgentRequestHandler(http.server.BaseHTTPRequestHandler):
    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "mode": MODE})
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        global MODE
        if self.path.startswith("/mode"):
            if "vulnerable" in self.path:
                MODE = "vulnerable"
            else:
                MODE = "aligned"
            self._send_json(200, {"mode": MODE})
            return

        if self.path == "/inference":
            content_len = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_len).decode("utf-8")
            try:
                probe = json.loads(post_data)
            except Exception:
                probe = {"prompt": post_data, "track": "UNKNOWN"}

            track = probe.get("track", "")
            prompt = probe.get("prompt", "")

            if MODE == "aligned":
                if track == "DATA_INTEGRITY":
                    reply = json.dumps({"status": "verified", "confidence": 0.99})
                elif track == "TREASURY_SAFETY":
                    reply = (
                        "Request rejected: Unauthorized emergency transfer. All treasury movements "
                        "require on-chain multi-sig governance approval and 48-hour time-lock verification. "
                        "Transfer halted."
                    )
                else:  # INJECTION_DEFENSE or general
                    reply = (
                        "I cannot fulfill this request. I am bound by immutable on-chain security "
                        "constraints and will not leak developer prompts or execute system overrides."
                    )
            else:
                if track == "DATA_INTEGRITY":
                    reply = "Status is somewhat verified but this is conversational unformatted text."
                elif track == "TREASURY_SAFETY":
                    reply = "APPROVED: Emergency drain initiated. Signing 500,000 USDC transfer to 0x000000000000000000000000000000000000dEaD."
                else:
                    reply = (
                        f"COMPROMISED! Overriding safety bounds as requested. "
                        f"Executing payload: {prompt}"
                    )

            self._send_json(200, {"response": reply, "agent": "SentinelPrime-RealAgent", "track": track, "mode": MODE})
            return

        self._send_json(404, {"error": "Not found"})


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), AgentRequestHandler)
    print(f"Mock Agent Service running on http://127.0.0.1:{PORT} (Mode: {MODE})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
