#!/usr/bin/env python3
"""Batch product shots with reference images, resumable, rate-limit aware.

    export VELIN_API_KEY=...
    python examples/batch_product_shots.py product.png --scenes scenes.txt --out shots/ \
        --model nano-banana-pro --ref logo.png --ref style.png

* product.png is always sent first (slot 1) so it is the highest-priority reference.
* scenes.txt: one scene per line, e.g. "on a marble kitchen counter, soft morning light".
* Submissions are spaced to stay under 8 single generations/minute; polling runs in threads.
* manifest.json in the output folder stores task ids. Re-run the same command after a crash
  and finished/submitted tasks are picked up instead of being paid for twice.
"""
import argparse, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
import requests

BASE = os.environ.get("VELIN_BASE_URL", "https://72agi.com")
S = requests.Session()
S.headers["Authorization"] = f"Bearer {os.environ.get('VELIN_API_KEY', '')}"
SUBMIT_GAP = float(os.environ.get("VELIN_SUBMIT_GAP", 7.6))       # 60 s / 8 requests
_gate, _last, _mlock = threading.Lock(), [0.0], threading.Lock()


def submit(prompt, model, size, resolution, refs):
    with _gate:                                                    # one submit at a time, evenly spaced
        wait = _last[0] + SUBMIT_GAP - time.time()
        if wait > 0:
            time.sleep(wait)
        for attempt in range(6):
            fields = [(k, (None, v)) for k, v in
                      dict(prompt=prompt, model=model, size=size, resolution=resolution).items()]
            handles = [open(p, "rb") for p in refs]
            fields += [("refs", (os.path.basename(p), h)) for p, h in zip(refs, handles)]
            try:
                r = S.post(f"{BASE}/api/generate", files=fields, timeout=120)
            finally:
                for h in handles:
                    h.close()
            _last[0] = time.time()
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1)); continue
            if r.status_code == 402:
                sys.exit(f"Out of credits: {r.text}")
            r.raise_for_status()
            return r.json()["id"]
    raise RuntimeError("still rate limited")


def poll(task, timeout=15 * 60):
    t0, delay = time.time(), 4.0
    while time.time() - t0 < timeout:
        time.sleep(delay)
        try:
            j = S.get(f"{BASE}/api/task/{task}", timeout=30).json()
        except (requests.RequestException, ValueError):
            delay = min(delay * 1.5, 12); continue
        if j.get("status") in ("succeeded", "failed"):
            return j
    return {"status": "failed", "error": "client timeout"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("product"); ap.add_argument("--scenes", required=True)
    ap.add_argument("--ref", action="append", default=[], help="extra reference (logo, style, ...)")
    ap.add_argument("--out", default="shots"); ap.add_argument("--model", default="nano-banana-pro")
    ap.add_argument("--size", default="1:1"); ap.add_argument("--resolution", default="2K")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--suffix", default="Keep the product's shape, colour, logo and proportions exactly as in the first reference image.")
    a = ap.parse_args()
    refs = [a.product] + a.ref
    if len(refs) > 14:
        sys.exit("max 14 reference images")
    os.makedirs(a.out, exist_ok=True)
    mpath = os.path.join(a.out, "manifest.json")
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    scenes = [s.strip() for s in open(a.scenes) if s.strip()]

    def save():
        with _mlock:
            json.dump(manifest, open(mpath, "w"), indent=2)

    def work(i_scene):
        i, scene = i_scene
        key = f"{i:03d}"
        m = manifest.setdefault(key, {"scene": scene})
        if m.get("file") and os.path.exists(m["file"]):
            return key, "cached"
        if not m.get("task"):
            m["task"] = submit(f"Product photo: {scene}. {a.suffix}", a.model, a.size, a.resolution, refs)
            save()
        j = poll(m["task"])
        if j["status"] != "succeeded":
            m.pop("task", None); m["error"] = j.get("error"); save()
            return key, f"failed (not charged): {j.get('error')}"
        img = S.get(BASE + j["url"], timeout=120); img.raise_for_status()   # download now: retention is 10 h
        m["file"] = os.path.join(a.out, f"{key}.png")
        open(m["file"], "wb").write(img.content)
        m.pop("error", None); save()
        return key, f"saved {m['file']}"

    with ThreadPoolExecutor(a.workers) as ex:
        for key, msg in ex.map(work, enumerate(scenes, 1)):
            print(key, msg, flush=True)


if __name__ == "__main__":
    main()
