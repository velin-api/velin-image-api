# VELIN in SillyTavern (via a small local adapter)

SillyTavern has no built-in VELIN source and VELIN is not OpenAI-compatible (multipart submit + polling, images returned as a URL path, no CORS headers). The adapter in this folder bridges that gap: it pretends to be an **AUTOMATIC1111 / "Stable Diffusion WebUI"** backend, which SillyTavern's Image Generation extension already supports.

```
SillyTavern  --/sdapi/v1/txt2img-->  velin-sd-adapter.mjs (127.0.0.1:7861)  --POST /api/generate + poll-->  72agi.com
```

## Setup (Node 18+, no dependencies)

```bash
export VELIN_API_KEY="your key from https://72agi.com/me.html"
node velin-sd-adapter.mjs            # listens on http://127.0.0.1:7861
```

In SillyTavern: **Extensions -> Image Generation**
1. Source: **Stable Diffusion Web UI (AUTOMATIC1111)**
2. SD Web UI URL: `http://127.0.0.1:7861`
3. Press **Connect**. The "Model" dropdown now lists VELIN model ids (`gpt-image-2.5-flare`, `nano-banana-pro`, ...). Pick one.
4. Generate as usual (`/sd`, or the wand button). Expect **~45-100 s per image**.

Width/height are mapped to the nearest supported aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3). Resolution is fixed at 1K in the adapter; edit `form.set("resolution", "1K")` if you want 2K/4K (same price).

## Notes
- Keep the key in the adapter's environment, never in a character card or shared preset. The key also signs in to your VELIN account.
- The adapter listens on 127.0.0.1 only. Do not expose it to the internet: anyone who can reach it spends your credits.
- Failed generations are not charged. Content moderation follows the upstream model providers.
- One image at a time is the safe pattern; the API allows 8 single generations per minute per account.

## Test status
- **Tested:** the adapter's endpoints (`sd-models`, `options`, `txt2img` with submit -> poll -> download -> base64, ratio mapping, model switch) against a local mock of the VELIN API (`../tests/mock_velin.py`).
- **Not tested:** a real SillyTavern instance driving it, and a run against the live API with a real key. If you try it, please open an issue or a Discussion post with what you see.
