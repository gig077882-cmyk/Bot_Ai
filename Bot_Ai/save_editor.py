import os
import base64
import gzip
import re


XOR_KEY = 0x0B

# Resolution: -1=fullscreen, 1=640x480, 2=720x480, 3=800x600, 4=960x640, ...
RES_MAP = {
    1: "640x480",
    2: "720x480",
    3: "800x600",
    4: "960x640",
    5: "1024x768",
    6: "1152x864",
    7: "1280x720",
}


def get_save_path():
    base = os.path.expandvars(r"%LOCALAPPDATA%\GeometryDash")
    candidates = [
        os.path.join(base, "CCGameManager.dat"),
        os.path.join(base, "CCGameManager2.dat"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def decode_save(data):
    xored = bytes([b ^ XOR_KEY for b in data])
    b64_std = xored.replace(b"-", b"+").replace(b"_", b"/").rstrip(b"\x00")
    decoded = base64.b64decode(b64_std)
    return gzip.decompress(decoded).decode("utf-8")


def encode_save(text):
    compressed = gzip.compress(text.encode("utf-8"), compresslevel=9)
    b64_std = base64.b64encode(compressed)
    b64_url = b64_std.replace(b"+", b"-").replace(b"/", b"_")
    xored = bytes([b ^ XOR_KEY for b in b64_url])
    return xored


def read_save(path=None):
    if path is None:
        path = get_save_path()
    with open(path, "rb") as f:
        return decode_save(f.read())


def write_save(text, path=None):
    if path is None:
        path = get_save_path()
    data = encode_save(text)
    with open(path, "wb") as f:
        f.write(data)


def get_resolution(text):
    m = re.search(r"<k>resolution</k><i>([^<]+)</i>", text)
    if m:
        return int(m.group(1))
    return None


def set_resolution(text, res_value):
    return re.sub(
        r"<k>resolution</k><i>[^<]+</i>",
        f"<k>resolution</k><i>{res_value}</i>",
        text,
    )


def print_current_settings():
    text = read_save()
    res = get_resolution(text)
    res_str = RES_MAP.get(res, f"unknown({res})")
    print(f"Current resolution: {res} ({res_str})")
    print()
    print("Available modes:")
    for k, v in RES_MAP.items():
        mark = " <--" if k == res else ""
        print(f"  {k}: {v}{mark}")
    print("  -1: Fullscreen")


def set_windowed(resolution_id=3):
    text = read_save()
    old_res = get_resolution(text)
    text = set_resolution(text, resolution_id)
    write_save(text)
    new_str = RES_MAP.get(resolution_id, f"id={resolution_id}")
    old_str = RES_MAP.get(old_res, f"id={old_res}")
    print(f"Changed: {old_res} ({old_str}) -> {resolution_id} ({new_str})")


if __name__ == "__main__":
    import sys

    print("=== GD Save Editor ===")
    save_path = get_save_path()
    print(f"File: {save_path}")
    print()

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "show":
            print_current_settings()
        elif cmd == "windowed":
            res = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            set_windowed(res)
        elif cmd == "fullscreen":
            set_windowed(-1)
        else:
            print(f"Unknown: {cmd}")
    else:
        print_current_settings()
        print()
        print("Commands:")
        print("  python save_editor.py show")
        print("  python save_editor.py windowed [res_id]")
        print("  python save_editor.py fullscreen")
