#!/usr/bin/env node
// VELIN image generation example (async: submit a task, poll, download).
// Requires Node 18+ (built-in fetch / FormData / Blob). No dependencies.
//
//   export VELIN_API_KEY=your_key
//   node generate.mjs "a quiet room, cream light" --model gpt-image-2.5-flare \
//     --size 16:9 --resolution 1K --ref ./source.png --out out.png
import { readFile, writeFile } from "node:fs/promises";
import { basename } from "node:path";
import { parseArgs } from "node:util";

const BASE_URL = process.env.VELIN_BASE_URL || "https://72agi.com";
const MAX_WAIT_MS = 15 * 60 * 1000; // tasks normally finish in ~45-100 s (4K longer)
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const { values: opt, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    model: { type: "string", default: "gpt-image-2.5-flare" },
    size: { type: "string", default: "1:1" },
    resolution: { type: "string", default: "1K" },
    ref: { type: "string", multiple: true, default: [] },
    out: { type: "string" },
  },
});

const key = process.env.VELIN_API_KEY;
const die = (msg) => { console.error(msg); process.exit(1); };
if (!key) die("Set VELIN_API_KEY first");
const prompt = positionals.join(" ");
if (!prompt) die('Usage: node generate.mjs "your prompt" [--model ...]');
const auth = { Authorization: `Bearer ${key}` };

async function submit() {
  for (let attempt = 0; attempt < 5; attempt++) {
    // multipart/form-data body (rebuilt on each attempt)
    const form = new FormData();
    form.set("prompt", prompt);
    form.set("model", opt.model);
    form.set("size", opt.size);
    form.set("resolution", opt.resolution);
    for (const path of opt.ref) {
      // up to 14 reference images, each <= 8 MB
      form.append("refs", new Blob([await readFile(path)]), basename(path));
    }
    const res = await fetch(`${BASE_URL}/api/generate`, { method: "POST", headers: auth, body: form });
    if (res.status === 429) {
      const wait = Number(res.headers.get("retry-after")) || 10 * (attempt + 1);
      console.error(`429 rate limited, retrying in ${wait}s`);
      await sleep(wait * 1000);
      continue;
    }
    const body = await res.json().catch(() => ({}));
    if (res.status === 402) throw new Error(`Insufficient credits: need ${body.need}, have ${body.have}`);
    if (!res.ok) throw new Error(`Submit failed (HTTP ${res.status}): ${body.error ?? res.statusText}`);
    return body.id;
  }
  throw new Error("Still rate limited after retries");
}

async function poll(id) {
  const started = Date.now();
  let delay = 3000;
  while (Date.now() - started < MAX_WAIT_MS) {
    await sleep(delay);
    let res, job;
    try {
      res = await fetch(`${BASE_URL}/api/task/${id}`, { headers: auth });
      job = await res.json();
    } catch (e) {
      console.error(`poll error (${e.message}), retrying`);
      delay = Math.min(delay * 1.5, 15000);
      continue;
    }
    console.error(`[${Math.round((Date.now() - started) / 1000)}s] ${job.status}`);
    if (job.status === "succeeded") return job;
    if (job.status === "failed") throw new Error(`Generation failed (not charged): ${job.error}`);
    if (res.status === 404) throw new Error(`Unknown task: ${job.error}`);
    delay = Math.min(delay * 1.5, 10000); // 3s -> 4.5s -> ... capped at 10s
  }
  throw new Error(`Timed out; task ${id} may be stuck`);
}

async function main() {
  const id = await submit();
  console.error(`task ${id} queued`);
  const job = await poll(id);

  const imageUrl = BASE_URL + job.url; // url is a site-relative path like /outputs/<id>.png
  const out = opt.out || basename(job.url);
  const img = await fetch(imageUrl, { headers: auth });
  if (!img.ok) throw new Error(`Download failed (HTTP ${img.status})`);
  await writeFile(out, Buffer.from(await img.arrayBuffer()));
  console.log(`saved ${out} (${imageUrl}, price ${job.price} CNY)`);
}

main().catch((e) => die(e.message));
