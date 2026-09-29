# VELIN Image API: Developer Integration Kit

**VELIN** ([72agi.com](https://72agi.com)) is a pay-per-image AI image generation API. One API key, one simple async endpoint, and seven models, including Nano Banana Pro, Nano Banana 2 and GPT Image 2 / 2.5. You pay per image and **the price is the same at 1K, 2K and 4K**.

- **From about $0.037 per image**, with no subscription
- **Failed generations are not charged.** Credits are refunded automatically.
- **Up to 14 reference images** per request (image-to-image / style / composition)
- **Capacity up to 100,000 images/day.** Volume pricing is negotiable.
- **Free test on request: message [@ayan8866e](https://t.me/ayan8866e) on Telegram**
- Support / volume deals: Telegram **[@ayan8866e](https://t.me/ayan8866e)**

```
.
├── README.md                     ← you are here
├── curl.sh                       ← bash + curl + jq
├── generate.py                   ← Python 3 + requests
├── generate.mjs                  ← Node 18+ (built-in fetch, no deps)
├── n8n-velin-image-workflow.json ← importable n8n workflow
└── SILLYTAVERN.md                ← notes for SillyTavern users
```

---

## Quickstart

### 1. Get your API key

1. Sign in at **https://72agi.com**.
2. Open **My account** (`https://72agi.com/me.html`) and press **Copy** next to your key.
3. Store it in an environment variable:

```bash
export VELIN_API_KEY="paste-your-key-here"
```

> ⚠️ **Treat the key like a password.** It calls the API *and* signs in to your account. Keep it on your server and never put it in front-end code or URLs. If it leaks, press **replace** on My account and the old key stops working immediately.

### 2. Authenticate

Every request sends one header:

```
Authorization: Bearer <VELIN_API_KEY>
```

Base URL: `https://72agi.com`

### 3. Create a task

`POST /api/generate` takes a **multipart/form-data** body:

```bash
curl -X POST https://72agi.com/api/generate \
  -H "Authorization: Bearer $VELIN_API_KEY" \
  -F "prompt=a quiet room, cream light" \
  -F "model=gpt-image-2.5-flare" \
  -F "size=16:9" \
  -F "resolution=1K"
```

Response `202`:

```json
{"id": "02a38b1d1b66", "status": "queued"}
```

With reference images, repeat the `refs` field (max 14 files, 8 MB each):

```bash
curl -X POST https://72agi.com/api/generate \
  -H "Authorization: Bearer $VELIN_API_KEY" \
  -F "prompt=turn this into a watercolour" \
  -F "model=gpt-image-2.5-sunburst" \
  -F "refs=@./source.png"
```

### 4. Poll until it's done

`GET /api/task/{id}`. Poll every 3–5 seconds.

```bash
curl https://72agi.com/api/task/02a38b1d1b66 -H "Authorization: Bearer $VELIN_API_KEY"
```

```json
{"id": "02a38b1d1b66", "status": "processing"}
```

```json
{"id": "02a38b1d1b66", "status": "succeeded", "url": "/outputs/02a38b1d1b66.png", "price": 0.25}
```

| `status` | Meaning |
|---|---|
| `queued` | Accepted and waiting |
| `processing` | Generating |
| `succeeded` | Done. `url` and `price` (CNY) are present. |
| `failed` | Not charged. The reason is in `error`. |

A typical image takes **about 45–100 seconds**, depending on the model (4K takes longer). Don't hold a synchronous request open. Use polling. Tasks survive client disconnects, so you can resume polling with the same `id`.

### 5. Download the image

`url` is a **path on the site**, not a full URL. Prepend the base URL:

```bash
curl -o image.png "https://72agi.com/outputs/02a38b1d1b66.png"
```

The API does not return base64. Download from the URL.

**Download promptly.** Generated images are deleted after 10 hours by default (see [Data retention](#faq)).

### Run the ready-made examples

```bash
# Python
pip install requests
python generate.py "a red fox in fresh snow, golden hour" --model nano-banana-pro --size 3:2 --resolution 2K

# Node 18+
node generate.mjs "a red fox in fresh snow, golden hour" --model nano-banana-pro --size 3:2 --resolution 2K

# curl + jq
./curl.sh "a red fox in fresh snow, golden hour" nano-banana-pro 3:2 2K
```

Python and Node accept `--ref path.png` (repeatable) for reference images and `--out file.png`. All three read the key from `VELIN_API_KEY`, poll with backoff, handle 402/429/failed, and save the image.

---

## Pricing

Credits are held in CNY. Each task's `price` is reported in CNY. Top-up is in **USDT**; card payments are **coming soon**.

| Model | Price / image | ≈ USD | 1K / 2K / 4K |
|---|---|---|---|
| Nano Banana Pro | ¥0.25 | ~$0.037 | same price |
| Nano Banana 2 | ¥0.25 | ~$0.037 | same price |
| GPT Image 2 | ¥0.25 | ~$0.037 | same price |
| GPT Image 2.5 Flare | ¥0.25 | ~$0.037 | same price |
| GPT Image 2.5 Sunburst | ¥0.25 | ~$0.037 | same price |
| Nano Banana Pro+ | ¥0.35 | ~$0.052 | same price |
| Nano Banana 2+ | ¥0.35 | ~$0.052 | same price |

- USD figures are approximate. At the time of writing, the billing page converts at 6.7 CNY per USDT. For example, a 100-image pack is 3.74 USDT and a 500-image pack is 18.66 USDT.
- Credits are **deducted when you submit** and **refunded automatically if the task fails**.
- Live prices come from `GET /api/models`. The price returned at order time is authoritative, so don't hard-code prices in your app.
- Check your balance with `GET /api/credits` (see below).
- **Volume / reseller pricing:** negotiable. Contact Telegram [@ayan8866e](https://t.me/ayan8866e).

### Check your credits

```bash
curl https://72agi.com/api/credits -H "Authorization: Bearer $VELIN_API_KEY"
# {"credits": 29.75, "unlimited": false, "role": "user"}   <- balance in CNY
```

```python
import os, requests
r = requests.get("https://72agi.com/api/credits",
                 headers={"Authorization": f"Bearer {os.environ['VELIN_API_KEY']}"}, timeout=30)
r.raise_for_status()
print(r.json()["credits"], "CNY")
```

```js
const r = await fetch("https://72agi.com/api/credits", {
  headers: { Authorization: `Bearer ${process.env.VELIN_API_KEY}` },
});
console.log((await r.json()).credits, "CNY");
```

---

## Models

`GET /api/models` (no auth required) returns the live list with `id`, `name` and `prices`.

| `model` id | Name | Notes |
|---|---|---|
| `nano-banana-pro` | Nano Banana Pro | Rich detail: posters, product, art |
| `nano-banana-2` | Nano Banana 2 | Fast: avatars, social, quick drafts |
| `nano-banana-pro-plus` | Nano Banana Pro+ | "+" variant of Nano Banana Pro |
| `nano-banana-2-plus` | Nano Banana 2+ | "+" variant of Nano Banana 2; also supports extreme ratios 1:8 / 8:1 |
| `gpt-image-2` | GPT Image 2 | Fourteen aspect ratios |
| `gpt-image-2.5-flare` | GPT Image 2.5 Flare | Fastest 2.5, ~45 s. Good default. |
| `gpt-image-2.5-sunburst` | GPT Image 2.5 Sunburst | Highest detail, ~100 s |

### Request fields (`POST /api/generate`, multipart/form-data)

| Field | Required | Description |
|---|---|---|
| `prompt` | yes | Image description (English or Chinese) |
| `model` | yes | A model `id` from the table above / `GET /api/models` |
| `size` | no | Aspect ratio: `1:1` (default), `16:9`, `9:16`, `4:3`, `3:4`, `3:2`, `2:3`. Some models support more; see below. |
| `resolution` | no | `1K` (default), `2K` or `4K`. Same price; higher is slower. |
| `refs` | no | Reference image file. Repeat the field for multiple images (max 14, each ≤ 8 MB; extras are ignored). More refs means slower generation. |

Defaults: `size=1:1` and `resolution=1K` if omitted. The examples always send both explicitly. **Nano Banana 2+** also supports extreme ratios `1:8` and `8:1`. **GPT Image 2** supports additional aspect ratios; call `GET /api/models` or ask on Telegram for the current list.

---

## Limits

| Limit | Value |
|---|---|
| Rate limit (default) | **8 single-image generations per minute** per account (batch: 2 runs/minute). Over the limit you get HTTP `429`. |
| Reference images | 14 per request, 8 MB each |
| Generation time | ~45–100 s typical; 4K and many refs take longer |
| Stuck tasks | If a task hasn't finished after ~13 minutes, treat it as failed. Credits for failed tasks are refunded. |
| Daily capacity | Up to 100,000 images/day. Contact us for higher rate limits. |
| Image retention | 10 hours by default, then deleted |

---

## Error handling

Errors are JSON with an `error` field. **Note:** `error` messages are currently written in Chinese (e.g. `"请先登录。"` = "please sign in"), so branch on the **HTTP status**, not on the message text.

| HTTP | When | What to do |
|---|---|---|
| `202` | Task created | Read `id` and start polling |
| `401` | Missing/invalid key → `{"error": "..."}` | Check `Authorization: Bearer <key>`; rotate the key if needed |
| `402` | Not enough credits → body includes `need` and `have` | Top up (USDT) at 72agi.com, then retry |
| `404` | `GET /api/task/{id}` for an unknown id → `{"error": "unknown job"}` | Check the id |
| `429` | Rate limit exceeded | Back off and retry (our examples wait 10 s, 20 s, …) |
| other 4xx/5xx | Validation or server error | Log `error`. Retry 5xx with backoff. |
| `status: "failed"` | Generation failed | Not charged. Read `error`, adjust the prompt, or retry. |

**Recommended client logic** (implemented in the examples):

1. Submit. On `429`, wait and retry. On `402`, stop and top up.
2. Poll `GET /api/task/{id}`, starting at 3 s and backing off to ~10 s. Tolerate transient network errors.
3. Stop on `succeeded` (download `https://72agi.com` + `url`) or `failed` (show `error`).
4. Give up after ~15 minutes.
5. Don't blindly re-submit after a network error on `POST /api/generate`. You may create a duplicate task. Check `GET /api/credits` or your gallery first.

**Call the API from your backend.** The API doesn't send CORS headers, so browser JavaScript on another domain can't call it directly. This also keeps your key off the client.

---

## Other endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /api/models` | no | Model list with ids and prices |
| `GET /api/credits` | yes | Balance (CNY) |
| `POST /api/gallery/{id}/keep` | yes | Opt in to keeping a generated image beyond the default 10-hour retention |

---

## FAQ

**Why is it so cheap?**
We have stable bulk supply, and we pass the savings on as a flat per-image price. It's the same price at 1K, 2K and 4K.

**Do I pay for failed generations?**
No. Credits are reserved when you submit and refunded automatically if the task fails.

**What happens to my prompts and images? (Data retention)**
Prompts and generated images are deleted after 10 hours. Download anything you want to keep. If you explicitly want an image kept longer, call `POST /api/gallery/{id}/keep`.

**Is there content moderation?**
Yes. Content moderation is the same as the official model providers'. Prompts or references that the official services would refuse will fail, and failed tasks aren't charged.

**Is it OpenAI-compatible?**
No. VELIN has its own small REST API: a multipart `POST` to create a task, then `GET` to poll. The examples in this kit cover curl, Python, Node and n8n. Porting to other languages takes about 50 lines.

**Why async instead of a single request?**
High-quality images take ~45–100 s. Holding HTTP connections open that long is fragile (proxies and serverless timeouts). With polling, a dropped connection never loses your image.

**How do I pay?**
Top up with **USDT** on the billing page (on-chain, credited automatically). Card payments are **coming soon**.

**Can I get free credits to test?**
Free test on request: message **[@ayan8866e](https://t.me/ayan8866e)** on Telegram. For anything else, including higher rate limits, reseller terms and volume pricing up to 100k images/day, message **[@ayan8866e](https://t.me/ayan8866e)** on Telegram.

**Can I resell or build a product on it?**
Yes. VELIN is built for developers and resellers. Volume pricing is negotiable on Telegram.

---

## No-code / tools

- **n8n:** import `n8n-velin-image-workflow.json`. Setup:
  1. In n8n go to **Credentials → New → Header Auth**. Set Name = `Authorization` and Value = `Bearer <your VELIN key>`, and save it as `VELIN API Key`.
  2. Import the workflow. Open **Create Task** and **Get Task** and select that credential. n8n will flag them until you do, because the file contains no real credential.
  3. Run it with **Manual Trigger** (edit defaults in **Set Params**), or POST JSON `{"prompt": "...", "model": "...", "size": "1:1", "resolution": "1K"}` to the **Webhook** URL. The output item contains `imageUrl`, `taskId` and `priceCny`.

  The workflow polls every 10 s and stops with an error if the task fails or runs longer than ~15 min. The webhook responds only when the image is ready (~1–2 min), so make sure your caller's HTTP timeout allows that.
- **SillyTavern:** see `SILLYTAVERN.md`.
