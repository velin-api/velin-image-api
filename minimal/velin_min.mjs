// Smallest useful VELIN client (Node 18+, no deps): submit -> poll -> save.
import { readFile, writeFile } from "node:fs/promises";
const BASE = process.env.VELIN_BASE_URL || "https://72agi.com";
const H = { Authorization: `Bearer ${process.env.VELIN_API_KEY}` };

export async function generate(prompt, { model = "nano-banana-pro", size = "1:1", resolution = "1K", refs = [], out = "out.png" } = {}) {
  const f = new FormData();
  for (const [k, v] of Object.entries({ prompt, model, size, resolution })) f.set(k, v);
  for (const p of refs) f.append("refs", new Blob([await readFile(p)]), p.split("/").pop()); // up to 14
  const r = await fetch(`${BASE}/api/generate`, { method: "POST", headers: H, body: f });
  if (!r.ok) throw new Error(`submit HTTP ${r.status}`);   // 401 bad key, 402 no credits, 429 slow down
  const { id } = await r.json();
  for (;;) {
    await new Promise((s) => setTimeout(s, 4000));
    const j = await (await fetch(`${BASE}/api/task/${id}`, { headers: H })).json();
    if (j.status === "failed") throw new Error(j.error);   // failed tasks are not charged
    if (j.status === "succeeded") {
      await writeFile(out, Buffer.from(await (await fetch(BASE + j.url, { headers: H })).arrayBuffer()));
      return out;
    }
  }
}

if (import.meta.url === `file://${process.argv[1]}`)
  console.log(await generate(process.argv.slice(2).join(" ") || "a red fox in fresh snow, golden hour"));
