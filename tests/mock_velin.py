#!/usr/bin/env python3
"""Tiny local stand-in for the VELIN API (no network, no credits).

Lets you run the examples in this repo offline:
    python tests/mock_velin.py            # listens on http://127.0.0.1:18787
    VELIN_BASE_URL=http://127.0.0.1:18787 VELIN_API_KEY=TESTKEY python generate.py "hello"

It mimics the documented contract only: multipart POST /api/generate -> 202 {id,status},
GET /api/task/{id} queued -> processing -> succeeded {url, price}, GET /outputs/<id>.png,
GET /api/credits, GET /api/models, 401 without the key, 429 after 8 submits/minute.
The "image" it returns is a generated solid-colour PNG. This is NOT the real service.
"""
import json, os, struct, sys, time, zlib
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEY = os.environ.get("MOCK_KEY", "TESTKEY")
PORT = int(os.environ.get("PORT", "18787"))
JOBS, SUBMITS = {}, []


def png(w=64, h=64, rgb=(200, 120, 60)):
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, code, obj=None, raw=None, ctype="application/json"):
        body = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authed(self):
        return self.headers.get("Authorization") == f"Bearer {KEY}"

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/api/models":
            return self.send(200, [{"id": m, "name": m, "prices": {"1K": 0.25, "2K": 0.25, "4K": 0.25}}
                                   for m in ("nano-banana-pro", "nano-banana-2", "gpt-image-2")])
        if not self.authed():
            return self.send(401, {"error": "请先登录。"})
        if p == "/api/credits":
            return self.send(200, {"credits": 29.75, "unlimited": False, "role": "user"})
        if p.startswith("/api/task/"):
            j = JOBS.get(p.rsplit("/", 1)[1])
            if not j:
                return self.send(404, {"error": "unknown job"})
            j["polls"] += 1
            if "FAIL" in j["prompt"]:
                return self.send(200, {"id": j["id"], "status": "failed", "error": "内容不符合要求"})
            if j["polls"] < 2:
                return self.send(200, {"id": j["id"], "status": "queued"})
            if j["polls"] < 3:
                return self.send(200, {"id": j["id"], "status": "processing"})
            return self.send(200, {"id": j["id"], "status": "succeeded", "url": f"/outputs/{j['id']}.png", "price": 0.25})
        if p.startswith("/outputs/"):
            return self.send(200, raw=png(rgb=(40 + 30 * (len(JOBS) % 6), 120, 200)), ctype="image/png")
        self.send(404, {"error": "not found"})

    def do_POST(self):
        p = self.path.split("?")[0]
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n)
        if not self.authed():
            return self.send(401, {"error": "请先登录。"})
        if p != "/api/generate":
            return self.send(404, {"error": "not found"})
        now = time.time()
        SUBMITS[:] = [t for t in SUBMITS if now - t < 60]
        if len(SUBMITS) >= 8:
            return self.send(429, {"error": "too many requests"})
        msg = BytesParser(policy=HTTP).parsebytes(
            b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + data)
        fields, refs = {}, 0
        for part in msg.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if name == "refs":
                refs += 1
            else:
                fields[name] = part.get_content()
        if not fields.get("prompt") or not fields.get("model"):
            return self.send(400, {"error": "prompt and model required"})
        SUBMITS.append(now)
        jid = "mock%04d" % len(JOBS)
        JOBS[jid] = {"id": jid, "polls": 0, "prompt": fields["prompt"]}
        print(f"SUBMIT {jid} model={fields['model']} size={fields.get('size')} res={fields.get('resolution')} refs={refs}",
              file=sys.stderr, flush=True)
        self.send(202, {"id": jid, "status": "queued"})


if __name__ == "__main__":
    print(f"mock VELIN on http://127.0.0.1:{PORT} (key: {KEY})", file=sys.stderr)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
