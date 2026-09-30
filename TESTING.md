# What was tested, and against what

Date: 2026-09-30. "Mock" = `tests/mock_velin.py`, a local server that implements the documented contract (multipart `POST /api/generate` -> 202, `GET /api/task/{id}` queued -> processing -> succeeded/failed, `GET /outputs/<id>.png`, 401 without the key, 429 after 8 submits/min). It returns a solid-colour PNG, not a real image.

| Item | Result | Against |
|---|---|---|
| `generate.py`, `generate.mjs` | submit -> poll -> download OK | mock |
| `minimal/velin_min.py`, `.mjs`, `.sh` | OK; 401 path OK | mock; 401 also against live API |
| `examples/batch_product_shots.py` | 4 scenes, 2 refs each: 3 saved, 1 failed task reported as not charged; re-run resumed from manifest with no new submissions | mock |
| `n8n-velin-image-workflow.json` | imported and executed with `n8n execute` in n8n 2.41.3 (Node 24): Manual Trigger -> Create Task -> Wait -> Get Task loop -> Image URL -> Download Image, status `success` | mock |
| `sillytavern/velin-sd-adapter.mjs` | `sd-models`, `options`, `txt2img` return valid base64 PNG, ratio mapped 1344x768 -> 16:9 | mock |
| `comfyui/ComfyUI-VELIN` | node registered in `/object_info`; LoadImage -> VELIN Generate Image (1 ref sent) -> SaveImage ran to success on ComfyUI (CPU) | mock |
| `GET /api/models`, 401 with a bad key, 404 for an unknown task id | matches docs | live API |

## Not tested
- A real generation with a real API key (this needs a funded account). Response shapes follow https://72agi.com/ai-connect.html; anything the docs don't publish is not asserted here (for example the exact aspect-ratio list for GPT Image 2).
- A real SillyTavern UI session with the adapter.
- n8n via the editor UI (CLI execution was used) and the webhook trigger path.
- ComfyUI desktop / ComfyUI-Manager installs.

If you run any of these against the live API and something differs, please open an issue.
