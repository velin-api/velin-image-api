# Migrating from gpt-image-1 (OpenAI lists it for shutdown on October 23, 2026)

OpenAI's [deprecations page](https://developers.openai.com/api/docs/deprecations) lists `gpt-image-1` for shutdown on **2026-10-23** (`gpt-image-1-mini` and `gpt-image-1.5` on 2026-12-01) and recommends `gpt-image-2.5-sunburst` or `gpt-image-2.5-flare`.
On VELIN both are ¥0.25 (≈ $0.037) per image at 1K/2K/4K. VELIN is not OpenAI-SDK compatible; it is a small async REST API:

| gpt-image-1 | VELIN |
|---|---|
| `client.images.generate(...)` (sync, base64) | `POST /api/generate` (multipart) → `GET /api/task/{id}` → download `url` |
| `size="1024x1536"` | `size=2:3` + `resolution=1K\|2K\|4K` (or `size=auto`) |
| `quality=low/medium/high` | none; one flat price |
| `images.edit(image=...)` | same endpoint, up to 14 `refs` files |

Code: see [`generate.py`](generate.py), [`generate.mjs`](generate.mjs), [`curl.sh`](curl.sh) and set `model=gpt-image-2.5-flare`.
Full guide: https://72agi.com/gpt-image-1-migration.html
