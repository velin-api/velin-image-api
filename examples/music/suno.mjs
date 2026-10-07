// Node 18+. export VELIN_API_KEY=... ; node suno.mjs "upbeat synthwave intro for a podcast"
import { writeFile } from "node:fs/promises";
const BASE = "https://72agi.com";
const H = { Authorization: `Bearer ${process.env.VELIN_API_KEY}`, "Content-Type": "application/json" };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const res = await fetch(`${BASE}/api/music`, { method: "POST", headers: H,
  body: JSON.stringify({ model: "suno-v5.5", prompt: process.argv[2] ?? "chill lo-fi beat", instrumental: false }) });
if (res.status === 402) throw new Error("Not enough credits: https://72agi.com/billing.html");
const { id } = await res.json();
let j;
do { await sleep(5000); j = await (await fetch(`${BASE}/api/music/${id}`, { headers: H })).json(); }
while (j.status === "queued" || j.status === "processing");
if (j.status !== "succeeded") throw new Error(`failed (not charged): ${j.error}`);
for (const t of j.tracks) {
  const mp3 = await fetch(BASE + t.audio_url, { headers: H });
  await writeFile(`${id}_${t.index}.mp3`, Buffer.from(await mp3.arrayBuffer()));
  console.log("saved", `${id}_${t.index}.mp3`, t.title);
}
