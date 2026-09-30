# ComfyUI-VELIN (draft custom node)

One node, **VELIN Generate Image** (category `VELIN`): prompt + model + aspect ratio + resolution, optional `reference_images` (IMAGE batch, up to 14) -> `IMAGE` + `task_info` string. It submits, polls and downloads inside the node, so a run takes ~45-100 s.

## Install
```bash
cd ComfyUI/custom_nodes
cp -r /path/to/velin-image-api/comfyui/ComfyUI-VELIN .
pip install -r ComfyUI-VELIN/requirements.txt   # requests, Pillow, numpy (torch comes with ComfyUI)
export VELIN_API_KEY="your key"                  # set before starting ComfyUI
```
The key is read from the environment on purpose: a key typed into a node widget would be saved in every workflow JSON you share. The model list is fetched live from `GET /api/models` (falls back to a built-in list when offline).

`workflow_api_example.json` is a minimal API-format workflow (LoadImage -> VELIN Generate Image -> SaveImage).

## Test status (read this)
- **Tested (ComfyUI, CPU, current master):** node loads and shows up in `/object_info`; the example workflow (LoadImage as reference -> node -> SaveImage) runs to `success` and saves a PNG, **against a local mock of the VELIN API** (`../tests/mock_velin.py`) that speaks the documented contract.
- **Not tested:** a run against the live VELIN API with a real key, and the ComfyUI desktop/Manager install path. Error handling for 401/402/429/failed follows the docs but has only been exercised for the happy path plus mock failures.
- Draft quality: no batch (list) output, no progress bar, always re-runs (each run is a new paid generation).
