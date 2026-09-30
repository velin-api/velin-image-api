# Using VELIN with SillyTavern: honest notes

**Short version:** SillyTavern has **no built-in VELIN source**, and you can't plug VELIN in by pasting a key. It is possible, but it needs a small adapter (or a community extension plus a proxy). This page explains why and what would be needed.

## Why it doesn't work out of the box

SillyTavern's built-in **Image Generation** extension talks to a fixed list of providers (Stable Diffusion WebUI, ComfyUI, NovelAI, OpenAI, Pollinations, FAL.AI, etc.). Each one uses its own request format. VELIN is different:

- **Not OpenAI-compatible.** It's VELIN's own API: a multipart `POST /api/generate` followed by polling `GET /api/task/{id}`.
- **Asynchronous.** An image takes ~45–100 s, and you have to poll for the result.
- **Returns a URL path**, not base64 (`/outputs/<id>.png` on `https://72agi.com`).
- **No CORS headers.** SillyTavern extensions that call APIs directly from the browser can't reach VELIN without a server-side proxy.

## What would work

**Option A: small local adapter (most robust).**
Run a tiny local service (~60 lines of Python or Node) that pretends to be a backend SillyTavern already supports. For example, it could expose the Stable Diffusion WebUI `POST /sdapi/v1/txt2img` endpoint. Then point SillyTavern's *Image Generation → Source: Stable Diffusion WebUI* URL at it. The adapter would:
1. take the prompt (and width/height → map to a VELIN `size` such as `1:1`/`16:9`/`9:16`),
2. call `POST /api/generate` with your `VELIN_API_KEY`,
3. poll `GET /api/task/{id}` until `succeeded`,
4. download `https://72agi.com` + `url` and return it as base64 in `{"images": ["..."]}`.

The polling and download logic is exactly what `generate.py` and `generate.mjs` already do. SillyTavern will wait ~1–2 min per image, so make sure no timeout in between is shorter than that. This kit now ships such an adapter: see [`sillytavern/`](sillytavern/README.md). It has been tested against a mock of the VELIN API, not yet with a real SillyTavern session.

**Option B: community extension + proxy.**
Some community image extensions advertise a configurable "custom API" mode with multipart uploads and async polling. Because these run in the browser, VELIN's missing CORS headers mean you'd still need a small proxy in front of `https://72agi.com`. We haven't tested any of them.

**Option C: no integration.**
Generate images with `generate.py` (or the n8n workflow) and attach them to the chat manually.

## Keep your key safe

Your VELIN key can also sign in to your account. Keep it in the adapter/proxy's environment (`VELIN_API_KEY`), never in a shared SillyTavern config, character card, or preset.
