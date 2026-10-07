#!/usr/bin/env node
// Minimal zero-dependency MCP server (stdio, JSON-RPC) for VELIN: generate_image, generate_music, get_balance.
// Node 18+. Claude Desktop / Cursor config:
//   {"mcpServers":{"velin":{"command":"node","args":["/path/to/velin-mcp.mjs"],"env":{"VELIN_API_KEY":"..."}}}}
// Every generation costs credits (image ~$0.037, music ~$0.12). Results are saved to VELIN_OUT_DIR (default cwd).
import { writeFile } from "node:fs/promises";
import { join } from "node:path";
import { createInterface } from "node:readline";

const BASE = "https://72agi.com";
const KEY = process.env.VELIN_API_KEY;
const OUT = process.env.VELIN_OUT_DIR || process.cwd();
const auth = { Authorization: `Bearer ${KEY}` };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const TOOLS = [
  { name: "generate_image", description: "Generate an image with VELIN (Nano Banana Pro/2, GPT Image 2/2.5). Costs ~$0.037. Saves a PNG and returns its path.",
    inputSchema: { type: "object", required: ["prompt"], properties: {
      prompt: { type: "string" },
      model: { type: "string", default: "gpt-image-2.5-flare", enum: ["gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-image-2", "nano-banana-pro", "nano-banana-2", "nano-banana-pro-plus", "nano-banana-2-plus"] },
      size: { type: "string", default: "1:1", description: "aspect ratio, e.g. 1:1, 16:9, 9:16, or auto" },
      resolution: { type: "string", enum: ["1K", "2K", "4K"], default: "1K" } } } },
  { name: "generate_music", description: "Generate a song with Suno 5.5/5 via VELIN. Costs ~$0.12, returns 2 mp3 tracks saved to disk.",
    inputSchema: { type: "object", required: ["prompt"], properties: {
      prompt: { type: "string", description: "song description, max 500 chars" },
      model: { type: "string", enum: ["suno-v5.5", "suno-v5"], default: "suno-v5.5" },
      instrumental: { type: "boolean", default: false } } } },
  { name: "get_balance", description: "Return the VELIN credit balance (CNY).", inputSchema: { type: "object", properties: {} } },
];

async function poll(url, timeoutMs) {
  const end = Date.now() + timeoutMs;
  while (Date.now() < end) {
    await sleep(5000);
    const j = await (await fetch(url, { headers: auth })).json();
    if (j.status === "succeeded") return j;
    if (j.status === "failed") throw new Error(`generation failed (not charged): ${j.error}`);
  }
  throw new Error("timed out; the job may still finish, check later");
}
async function save(path, name) {
  const r = await fetch(BASE + path, { headers: auth });
  const f = join(OUT, name); await writeFile(f, Buffer.from(await r.arrayBuffer())); return f;
}
async function call(name, a = {}) {
  if (!KEY) throw new Error("VELIN_API_KEY is not set");
  if (name === "get_balance") return JSON.stringify(await (await fetch(`${BASE}/api/credits`, { headers: auth })).json());
  if (name === "generate_image") {
    const form = new FormData();
    form.set("prompt", a.prompt); form.set("model", a.model || "gpt-image-2.5-flare");
    form.set("size", a.size || "1:1"); form.set("resolution", a.resolution || "1K");
    const r = await fetch(`${BASE}/api/generate`, { method: "POST", headers: auth, body: form });
    if (!r.ok) throw new Error(`submit failed ${r.status}: ${await r.text()}`);
    const { id } = await r.json();
    const j = await poll(`${BASE}/api/task/${id}`, 10 * 60e3);
    return `Saved ${await save(j.url, `${id}.png`)} (price ¥${j.price})`;
  }
  if (name === "generate_music") {
    const r = await fetch(`${BASE}/api/music`, { method: "POST", headers: { ...auth, "Content-Type": "application/json" },
      body: JSON.stringify({ model: a.model || "suno-v5.5", prompt: a.prompt, instrumental: !!a.instrumental }) });
    if (!r.ok) throw new Error(`submit failed ${r.status}: ${await r.text()}`);
    const { id } = await r.json();
    const j = await poll(`${BASE}/api/music/${id}`, 15 * 60e3);
    const files = [];
    for (const t of j.tracks) files.push(`${await save(t.audio_url, `${id}_${t.index}.mp3`)} (${t.title})`);
    return "Saved:\n" + files.join("\n");
  }
  throw new Error(`unknown tool ${name}`);
}

const send = (m) => process.stdout.write(JSON.stringify(m) + "\n");
createInterface({ input: process.stdin }).on("line", async (line) => {
  let msg; try { msg = JSON.parse(line); } catch { return; }
  const { id, method, params } = msg;
  if (id === undefined) return; // notification
  try {
    if (method === "initialize") return send({ jsonrpc: "2.0", id, result: {
      protocolVersion: params?.protocolVersion || "2025-06-18", capabilities: { tools: {} },
      serverInfo: { name: "velin", version: "0.1.0" } } });
    if (method === "tools/list") return send({ jsonrpc: "2.0", id, result: { tools: TOOLS } });
    if (method === "tools/call") {
      try { return send({ jsonrpc: "2.0", id, result: { content: [{ type: "text", text: await call(params.name, params.arguments) }] } }); }
      catch (e) { return send({ jsonrpc: "2.0", id, result: { content: [{ type: "text", text: String(e.message || e) }], isError: true } }); }
    }
    if (method === "ping") return send({ jsonrpc: "2.0", id, result: {} });
    send({ jsonrpc: "2.0", id, error: { code: -32601, message: "method not found" } });
  } catch (e) { send({ jsonrpc: "2.0", id, error: { code: -32603, message: String(e) } }); }
});
