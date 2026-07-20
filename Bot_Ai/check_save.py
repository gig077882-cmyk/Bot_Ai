import os, base64, gzip, re

path = os.path.expandvars(r"%LOCALAPPDATA%\GeometryDash\CCGameManager.dat")
with open(path, "rb") as f:
    data = f.read()

xored = bytes([b ^ 0x0B for b in data])
b64_std = xored.replace(b"-", b"+").replace(b"_", b"/").rstrip(b"\x00")
decoded = base64.b64decode(b64_std)
text = gzip.decompress(decoded).decode("utf-8")

keywords = ["full", "screen", "display", "window", "mode", "graphic"]
for kw in keywords:
    matches = re.findall(r"<k>[^<]*" + kw + r"[^<]*</k>", text, re.IGNORECASE)
    if matches:
        for m in matches:
            val_match = re.search(re.escape(m) + r"<i>([^<]+)</i>|<s>([^<]*)</s>", text)
            val = val_match.group(1) or val_match.group(2) if val_match else "?"
            print(f"  {m} = {val}")
    else:
        print(f"  No '{kw}' keys")
