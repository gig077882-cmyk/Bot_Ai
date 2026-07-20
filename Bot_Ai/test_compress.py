import os, base64, gzip, re

path = os.path.expandvars(r"%LOCALAPPDATA%\GeometryDash\CCGameManager2.dat")
with open(path, "rb") as f:
    orig_data = f.read()

xored = bytes([b ^ 0x0B for b in orig_data])
b64_std = xored.replace(b"-", b"+").replace(b"_", b"/").rstrip(b"\x00")
decoded = base64.b64decode(b64_std)
text = gzip.decompress(decoded).decode("utf-8")

print(f"Original gzip size: {len(decoded)} bytes")
print(f"Text size: {len(text)} bytes")
m = re.search(r"<k>resolution</k><i>([^<]+)</i>", text)
print(f"Resolution: {m.group(1)}")

text = re.sub(
    r"<k>resolution</k><i>[^<]+</i>",
    "<k>resolution</k><i>3</i>",
    text,
)

for level in range(0, 10):
    c = gzip.compress(text.encode(), compresslevel=level)
    diff = len(c) - len(decoded)
    print(f"  Level {level}: {len(c)} bytes (diff: {diff})")
