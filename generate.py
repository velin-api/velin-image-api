#!/usr/bin/env python3
"""VELIN image generation example (async: submit a task, poll, download).

Usage:
    export VELIN_API_KEY=your_key
    pip install requests
    python generate.py "a quiet room, cream light" --model gpt-image-2.5-flare \
        --size 16:9 --resolution 1K --ref ./source.png --out out.png
"""
import argparse
import os
import sys
import time

import requests

BASE_URL = os.environ.get("VELIN_BASE_URL", "https://72agi.com")
MAX_WAIT_S = 15 * 60  # tasks normally finish in ~45-100 s (4K longer)


def submit(session, prompt, model, size, resolution, refs):
    # The API expects multipart/form-data. (None, value) sends a plain form field.
    fields = [
        ("prompt", (None, prompt)),
        ("model", (None, model)),
        ("size", (None, size)),
        ("resolution", (None, resolution)),
    ]
    for path in refs:  # up to 14 reference images, each <= 8 MB
        fields.append(("refs", (os.path.basename(path), open(path, "rb"))))

    for attempt in range(5):
        r = session.post(f"{BASE_URL}/api/generate", files=fields, timeout=60)
        if r.status_code == 429:  # rate limited: 8 single generations / minute
            wait = int(r.headers.get("Retry-After", 10 * (attempt + 1)))
            print(f"429 rate limited, retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
            for _, (_, f, *rest) in fields:  # rewind file handles before resending
                if hasattr(f, "seek"):
                    f.seek(0)
            continue
        body = r.json() if r.content else {}
        if r.status_code == 402:
            sys.exit(f"Insufficient credits: need {body.get('need')}, have {body.get('have')}")
        if not r.ok:
            sys.exit(f"Submit failed (HTTP {r.status_code}): {body.get('error', r.text)}")
        return body["id"]
    sys.exit("Still rate limited after retries")


def poll(session, task_id):
    delay, started = 3.0, time.time()
    while time.time() - started < MAX_WAIT_S:
        time.sleep(delay)
        try:
            r = session.get(f"{BASE_URL}/api/task/{task_id}", timeout=30)
            job = r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"poll error ({e}), retrying", file=sys.stderr)
            delay = min(delay * 1.5, 15)
            continue
        status = job.get("status")
        print(f"[{int(time.time() - started)}s] {status}", file=sys.stderr)
        if status == "succeeded":
            return job
        if status == "failed":
            sys.exit(f"Generation failed (not charged): {job.get('error')}")
        if r.status_code == 404:
            sys.exit(f"Unknown task: {job.get('error')}")
        delay = min(delay * 1.5, 10)  # 3s -> 4.5s -> ... capped at 10s
    sys.exit(f"Timed out after {MAX_WAIT_S}s; task {task_id} may be stuck")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt")
    p.add_argument("--model", default="gpt-image-2.5-flare")
    p.add_argument("--size", default="1:1", help="aspect ratio, e.g. 1:1, 16:9, 9:16")
    p.add_argument("--resolution", default="1K", choices=["1K", "2K", "4K"])
    p.add_argument("--ref", action="append", default=[], help="reference image (repeatable)")
    p.add_argument("--out", default=None)
    a = p.parse_args()

    key = os.environ.get("VELIN_API_KEY")
    if not key:
        sys.exit("Set VELIN_API_KEY first")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {key}"

    task_id = submit(s, a.prompt, a.model, a.size, a.resolution, a.ref)
    print(f"task {task_id} queued", file=sys.stderr)
    job = poll(s, task_id)

    image_url = BASE_URL + job["url"]  # url is a site-relative path like /outputs/<id>.png
    out = a.out or os.path.basename(job["url"])
    img = s.get(image_url, timeout=120)
    img.raise_for_status()
    with open(out, "wb") as f:
        f.write(img.content)
    print(f"saved {out} ({image_url}, price {job.get('price')} CNY)")


if __name__ == "__main__":
    main()
