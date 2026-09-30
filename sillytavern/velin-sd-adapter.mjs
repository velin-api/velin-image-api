#!/usr/bin/env node
// Minimal "Stable Diffusion WebUI"-style adapter for SillyTavern -> VELIN.
// Node 18+, no dependencies.
//   export VELIN_API_KEY=your_key
//   node velin-sd-adapter.mjs            # listens on http://127.0.0.1:7861
import http from "node:http";

const BASE = process.env.VELIN_BASE_URL || "https://72agi.com";
const KEY = process.env.VELIN_API_KEY;
const PORT = Number(process.env.PORT || 7861);
if (!KEY) { console.error("Set VELIN_API_KEY first"); process.exit(1); }

const auth = { Authorization: `Bearer ${KEY}` };
const MODELS = ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2",
                "nano-banana-2", "nano-banana-pro"];
let model = MODELS[0];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// width x height -> nearest supported VELIN aspect ratio
const RATIOS = { "1:1": 1, "16:9": 16 / 9, "9:16": 9 / 16, "4:3": 4 / 3, "3:4": 3 / 4, "3:2": 1.5, "2:3": 2 / 3 };
function nearestRatio(w, h) {
  const r = w / h;
  return Object.entries(RATIOS).sort((a, b) => Math.abs(a[1] - r) - Math.abs(b[1] - r))[0][0];
}

async function generate(prompt, w, h) {
  const form = new FormData();
  form.set("prompt", prompt);
  form.set("model", model);
  form.set("size", nearestRatio(w, h));
  form.set("resolution", "1K");
  const res = await fetch(`${BASE}/api/generate`, { method: "POST", headers: auth, body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(`submit HTTP ${res.status}: ${body.error ?? ""}`);
  for (let i = 0; i < 180; i++) {            // poll every 5 s, up to 15 min
    await sleep(5000);
    const job = await (await fetch(`${BASE}/api/task/${body.id}`, { headers: auth })).json();
    if (job.status === "succeeded") {
      const img = await fetch(BASE + job.url, { headers: auth });
      return Buffer.from(await img.arrayBuffer()).toString("base64");
    }
    if (job.status === "failed") throw new Error(`failed (not charged): ${job.error}`);
  }
  throw new Error("timed out");
}

const json = (res, code, obj) => {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(obj));
};

http.createServer(async (req, res) => {
  const path = new URL(req.url, "http://x").pathname;
  let raw = "";
  for await (const c of req) raw += c;
  const body = raw ? JSON.parse(raw) : {};
  try {
    if (path === "/sdapi/v1/options" && req.method === "POST") {
      if (MODELS.includes(body.sd_model_checkpoint)) model = body.sd_model_checkpoint;
      return json(res, 200, {});
    }
    if (path === "/sdapi/v1/options") return json(res, 200, { sd_model_checkpoint: model });
    if (path === "/sdapi/v1/sd-models") return json(res, 200, MODELS.map((m) => ({ title: m, model_name: m })));
    if (path === "/sdapi/v1/samplers") return json(res, 200, [{ name: "Euler" }]);
    if (path === "/sdapi/v1/schedulers") return json(res, 200, [{ name: "Automatic" }]);
    if (path === "/sdapi/v1/upscalers") return json(res, 200, [{ name: "None" }]);
    if (path === "/sdapi/v1/latent-upscale-modes") return json(res, 200, []);
    if (path === "/sdapi/v1/sd-vae" || path === "/sdapi/v1/sd-modules") return json(res, 200, []);
    if (path === "/sdapi/v1/progress") return json(res, 200, { progress: 0, state: { job_count: 0 } });
    if (path === "/sdapi/v1/interrupt") return json(res, 200, {});
    if (path === "/sdapi/v1/txt2img" && req.method === "POST") {
      const b64 = await generate(body.prompt, body.width || 1024, body.height || 1024);
      return json(res, 200, { images: [b64], parameters: {}, info: "{}" });
    }
    json(res, 404, { error: "not found" });
  } catch (e) {
    console.error(e.message);
    json(res, 500, { error: e.message });
  }
}).listen(PORT, "127.0.0.1", () => console.log(`VELIN adapter on http://127.0.0.1:${PORT}`));
