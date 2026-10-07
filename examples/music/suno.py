"""Suno 5.5 / Suno 5 via VELIN: one generation = 2 tracks, ~$0.12. Failed jobs are not charged.
pip install requests ; export VELIN_API_KEY=...
python suno.py "lo-fi hip hop beat for studying, soft rain" --instrumental
"""
import argparse, os, sys, time, requests

BASE = "https://72agi.com"
H = {"Authorization": f"Bearer {os.environ['VELIN_API_KEY']}"}

ap = argparse.ArgumentParser()
ap.add_argument("prompt", help="song description (simple mode) or lyrics (with --title/--style)")
ap.add_argument("--model", default="suno-v5.5", choices=["suno-v5.5", "suno-v5"])
ap.add_argument("--instrumental", action="store_true")
ap.add_argument("--title"); ap.add_argument("--style", help="custom mode: genre, mood, instruments")
a = ap.parse_args()

body = {"model": a.model, "prompt": a.prompt, "instrumental": a.instrumental}
if a.style or a.title:
    body.update(custom_mode=True, style=a.style or "", title=a.title or "Untitled")
r = requests.post(f"{BASE}/api/music", headers=H, json=body)
if r.status_code == 402:
    sys.exit("Not enough credits: top up at https://72agi.com/billing.html")
r.raise_for_status()
jid = r.json()["id"]; print("queued", jid)

deadline = time.time() + 15 * 60
while time.time() < deadline:
    time.sleep(5)
    j = requests.get(f"{BASE}/api/music/{jid}", headers=H).json()
    if j["status"] == "failed":
        sys.exit(f"failed (not charged): {j.get('error')}")
    if j["status"] == "succeeded":
        for t in j["tracks"]:
            fn = f"{jid}_{t['index']}.mp3"
            open(fn, "wb").write(requests.get(BASE + t["audio_url"], headers=H).content)
            print("saved", fn, "-", t.get("title"), round(t.get("duration") or 0), "s")
        break
