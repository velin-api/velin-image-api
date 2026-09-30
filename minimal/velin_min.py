"""Smallest useful VELIN client: submit -> poll -> save.  pip install requests"""
import os, sys, time, requests

BASE = os.environ.get("VELIN_BASE_URL", "https://72agi.com")
H = {"Authorization": f"Bearer {os.environ['VELIN_API_KEY']}"}

def generate(prompt, model="nano-banana-pro", size="1:1", resolution="1K", refs=(), out="out.png"):
    # The API wants multipart/form-data, so send every field via files= (plain data= would be urlencoded).
    fields = {"prompt": prompt, "model": model, "size": size, "resolution": resolution}
    files = [(k, (None, v)) for k, v in fields.items()]
    files += [("refs", (os.path.basename(p), open(p, "rb"))) for p in refs]         # up to 14
    r = requests.post(f"{BASE}/api/generate", headers=H, files=files, timeout=60)
    r.raise_for_status()                                  # 401 bad key, 402 no credits, 429 slow down
    task = r.json()["id"]
    while True:
        time.sleep(4)
        j = requests.get(f"{BASE}/api/task/{task}", headers=H, timeout=30).json()
        if j["status"] == "succeeded":
            break
        if j["status"] == "failed":                       # failed tasks are not charged
            raise RuntimeError(j.get("error"))
    open(out, "wb").write(requests.get(BASE + j["url"], headers=H, timeout=120).content)
    return out

if __name__ == "__main__":
    print(generate(" ".join(sys.argv[1:]) or "a red fox in fresh snow, golden hour"))
