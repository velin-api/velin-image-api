"""ComfyUI custom node for the VELIN image API (https://72agi.com).

One node, "VELIN Generate Image": submit -> poll -> download -> IMAGE tensor.
Reference images (up to 14) come in as a normal IMAGE batch.

The API key is read from the VELIN_API_KEY environment variable on purpose:
a key typed into a node widget would be saved inside every workflow JSON you share.
Optionally set VELIN_BASE_URL to point at another host (used for offline tests).
"""
import io
import os
import time

import numpy as np
import requests
import torch
from PIL import Image

BASE_URL_DEFAULT = "https://72agi.com"
MAX_WAIT_S = 15 * 60
MAX_REFS = 14

FALLBACK_MODELS = [
    "nano-banana-pro", "nano-banana-2", "gpt-image-2",
    "gpt-image-2.5-flare", "gpt-image-2.5-sunburst",
    "nano-banana-pro-plus", "nano-banana-2-plus",
]
RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"]


def _base():
    return os.environ.get("VELIN_BASE_URL", BASE_URL_DEFAULT).rstrip("/")


def _live_models():
    try:
        r = requests.get(f"{_base()}/api/models", timeout=5)
        ids = [m["id"] for m in r.json()]
        return ids or FALLBACK_MODELS
    except Exception:
        return FALLBACK_MODELS


def _tensor_to_png(t):
    arr = (t.detach().cpu().numpy().clip(0, 1) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _png_to_tensor(data):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    return torch.from_numpy(np.asarray(img).astype(np.float32) / 255.0)[None, ...]


class VelinGenerateImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "a red fox in fresh snow, golden hour"}),
                "model": (_live_models(),),
                "aspect_ratio": (RATIOS, {"default": "1:1"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
            },
            "optional": {
                "reference_images": ("IMAGE",),  # batch of up to 14 images
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("image", "task_info")
    FUNCTION = "run"
    CATEGORY = "VELIN"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")  # always re-run: every call is a new paid generation

    def run(self, prompt, model, aspect_ratio, resolution, reference_images=None):
        key = os.environ.get("VELIN_API_KEY")
        if not key:
            raise RuntimeError("Set the VELIN_API_KEY environment variable before starting ComfyUI.")
        headers = {"Authorization": f"Bearer {key}"}
        base = _base()

        fields = [(k, (None, v)) for k, v in
                  {"prompt": prompt, "model": model, "size": aspect_ratio, "resolution": resolution}.items()]
        n_refs = 0
        if reference_images is not None:
            for i in range(min(reference_images.shape[0], MAX_REFS)):
                fields.append(("refs", (f"ref{i}.png", _tensor_to_png(reference_images[i]), "image/png")))
                n_refs += 1

        for attempt in range(5):
            r = requests.post(f"{base}/api/generate", headers=headers, files=fields, timeout=120)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            break
        if r.status_code == 401:
            raise RuntimeError("VELIN: invalid or missing API key (HTTP 401)")
        if r.status_code == 402:
            b = r.json()
            raise RuntimeError(f"VELIN: not enough credits (need {b.get('need')}, have {b.get('have')})")
        if not r.ok:
            raise RuntimeError(f"VELIN submit failed (HTTP {r.status_code}): {r.text[:200]}")
        task = r.json()["id"]

        started, delay = time.time(), 3.0
        while time.time() - started < MAX_WAIT_S:
            time.sleep(delay)
            try:
                j = requests.get(f"{base}/api/task/{task}", headers=headers, timeout=30).json()
            except (requests.RequestException, ValueError):
                delay = min(delay * 1.5, 10)
                continue
            if j.get("status") == "succeeded":
                img = requests.get(base + j["url"], headers=headers, timeout=120)
                img.raise_for_status()
                info = f"task={task} model={model} refs={n_refs} price_cny={j.get('price')}"
                return (_png_to_tensor(img.content), info)
            if j.get("status") == "failed":
                raise RuntimeError(f"VELIN generation failed (not charged): {j.get('error')}")
            delay = min(delay * 1.3, 8)
        raise RuntimeError(f"VELIN task {task} did not finish in {MAX_WAIT_S // 60} minutes")


NODE_CLASS_MAPPINGS = {"VelinGenerateImage": VelinGenerateImage}
NODE_DISPLAY_NAME_MAPPINGS = {"VelinGenerateImage": "VELIN Generate Image"}
