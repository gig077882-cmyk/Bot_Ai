import subprocess
import time
import ctypes
import pydirectinput
import win32gui
import win32con
import yaml
import os

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [("type", ctypes.c_ulong), ("_input", _INPUT_UNION)]


def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)



def launch_gd(config, force_windowed=True):
    gd_path = config.get("gd_path", "C:/Users/GG/Desktop/Geometry Dash/GeometryDash.exe")
    res = config.get("window", {}).get("resolution", [800, 600])

    if not os.path.exists(gd_path):
        print(f"Error: GD not found at {gd_path}")
        return None

    print(f"Launching: {gd_path}")
    gd_dir = os.path.dirname(gd_path)
    subprocess.Popen([gd_path], cwd=gd_dir)

    print("Waiting for GD window...")
    hwnd = None
    for attempt in range(30):
        hwnd = find_gd_window(config)
        if hwnd:
            print(f"Found after ~{attempt+1}s")
            break
        time.sleep(1)

    if not hwnd:
        print("Could not find GD window. Available windows:")
        def list_windows(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                t = win32gui.GetWindowText(hwnd)
                if t:
                    print(f"  '{t}'")
        win32gui.EnumWindows(list_windows, None)
        return None

    bring_to_front(hwnd)
    time.sleep(0.2)

    if force_windowed:
        print("Forcing windowed mode...")
        for i in range(8):
            try:
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                if style & win32con.WS_POPUP:
                    style &= ~win32con.WS_POPUP
                    style |= win32con.WS_OVERLAPPED | win32con.WS_CAPTION | win32con.WS_SYSMENU | win32con.WS_MINIMIZEBOX
                    win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
                win32gui.SetWindowPos(hwnd, 0, 100, 50, res[0], res[1],
                    win32con.SWP_FRAMECHANGED | win32con.SWP_SHOWWINDOW)
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception:
                pass
            time.sleep(0.15)

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    print(f"Window: {res[0]}x{res[1]}")
    return hwnd


def send_alt_enter():
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    inputs = (INPUT * 4)()
    inputs[0] = INPUT(INPUT_KEYBOARD, ki=KEYBDINPUT(0x12, 0, 0, 0, None))
    inputs[1] = INPUT(INPUT_KEYBOARD, ki=KEYBDINPUT(0x0D, 0, 0, 0, None))
    inputs[2] = INPUT(INPUT_KEYBOARD, ki=KEYBDINPUT(0x0D, 0, KEYEVENTF_KEYUP, 0, None))
    inputs[3] = INPUT(INPUT_KEYBOARD, ki=KEYBDINPUT(0x12, 0, KEYEVENTF_KEYUP, 0, None))
    ctypes.windll.user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def find_gd_window(config):
    title = config["window"]["title"]
    title_alt = config["window"]["title_alt"]

    def callback(hwnd, result):
        text = win32gui.GetWindowText(hwnd)
        if title in text or title_alt in text:
            result.append(hwnd)

    result = []
    win32gui.EnumWindows(callback, result)
    return result[0] if result else None


def bring_to_front(hwnd):
    try:
        win32gui.ShowWindow(hwnd, 5)
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)
    except Exception:
        pass


def start_level(level_num=1, hwnd=None):
    if level_num < 1 or level_num > 22:
        level_num = 1

    if hwnd:
        bring_to_front(hwnd)
    time.sleep(0.3)

    pydirectinput.press("enter")
    time.sleep(0.4)
    pydirectinput.press("enter")
    time.sleep(0.4)

    for _ in range(level_num - 1):
        pydirectinput.press("right")
        time.sleep(0.1)

    pydirectinput.press("enter")
    time.sleep(0.5)

    print(f"Level {level_num} started!")
    return True


def start_practice(level_num=1, hwnd=None):
    if level_num < 1 or level_num > 22:
        level_num = 1

    if hwnd:
        bring_to_front(hwnd)
    time.sleep(0.3)

    pydirectinput.press("enter")
    time.sleep(0.4)
    pydirectinput.press("enter")
    time.sleep(0.4)

    for _ in range(level_num - 1):
        pydirectinput.press("right")
        time.sleep(0.1)

    pydirectinput.press("enter")
    time.sleep(0.4)
    pydirectinput.press("down")
    time.sleep(0.1)
    pydirectinput.press("enter")
    time.sleep(0.5)

    print(f"Practice mode - Level {level_num} started!")
    return True


def launch_and_train(level_num=1):
    config = load_config()
    hwnd = launch_gd(config)
    if not hwnd:
        print("Starting training anyway (GD must be open)...")
        time.sleep(2)
    else:
        time.sleep(1)
        start_level(level_num, hwnd)
        time.sleep(2)
    import train
    train.train()


def launch_and_play(level_num=1):
    config = load_config()
    hwnd = launch_gd(config)
    if not hwnd:
        print("Starting play anyway (GD must be open)...")
        time.sleep(2)
    else:
        time.sleep(1)
        start_level(level_num, hwnd)
        time.sleep(2)
    import play
    play.play()


def close_gd():
    def callback(hwnd, hwnds):
        if "Geometry Dash" in win32gui.GetWindowText(hwnd):
            hwnds.append(hwnd)

    hwnds = []
    win32gui.EnumWindows(callback, hwnds)
    for hwnd in hwnds:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        print("GD closed")


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]

    if not args:
        print("Commands:")
        print("  python launcher.py launch [level]")
        print("  python launcher.py launch_train [level]")
        print("  python launcher.py launch_play [level]")
        print("  python launcher.py practice [level]")
        print("  python launcher.py close")
        sys.exit(0)

    cmd = args[0]
    level = int(args[1]) if len(args) > 1 else 1
    config = load_config()

    if cmd == "launch":
        hwnd = launch_gd(config)
        if hwnd:
            start_level(level, hwnd)
    elif cmd == "practice":
        hwnd = launch_gd(config)
        if hwnd:
            start_practice(level, hwnd)
    elif cmd == "launch_train":
        launch_and_train(level)
    elif cmd == "launch_play":
        launch_and_play(level)
    elif cmd == "close":
        close_gd()
    else:
        print(f"Unknown: {cmd}")
