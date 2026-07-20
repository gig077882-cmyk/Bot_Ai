import time
import cv2
import numpy as np
import mss
import pydirectinput
import win32gui
import win32con
from collections import deque

pydirectinput.PAUSE = 0.0


class GeometryDashEnv:
    def __init__(self, config):
        self.config = config
        self.resize = (
            config["preprocessing"]["resize_width"],
            config["preprocessing"]["resize_height"],
        )
        self.stack_size = config["preprocessing"]["frame_stack"]
        self.action_repeat = config["action_repeat"]
        self.fps = config.get("fps", 60)
        self.dt = 1.0 / self.fps
        self.max_steps = config["training"]["max_steps_per_episode"]

        cap = config["screen"]["capture_region"]
        self.capture_region = tuple(cap)

        crop = config["screen"].get("gameplay_region", [0, 0, 800, 600])
        self.gameplay_crop = tuple(crop)
        self.crop_to_gameplay = config["screen"].get("crop_to_gameplay", True)

        self.sct = mss.mss()
        self.frames = deque(maxlen=self.stack_size)
        self.raw_frames = deque(maxlen=self.stack_size)
        self.step_count = 0
        self.last_progress = 0.0
        self.done = False
        self.death_cooldown = 0
        self.in_game = False
        self.window_handle = None
        self._find_window()
        self._ensure_foreground()

    def _find_window(self):
        title = self.config["window"]["title"]
        title_alt = self.config["window"]["title_alt"]

        def callback(hwnd, result):
            text = win32gui.GetWindowText(hwnd)
            if title in text or title_alt in text:
                result.append(hwnd)

        for attempt in range(20):
            result = []
            win32gui.EnumWindows(callback, result)
            if result:
                self.window_handle = result[0]
                return
            time.sleep(0.25)

        print("Warning: GD window not found. Using full screen.")

    def _is_foreground(self):
        if not self.window_handle:
            return False
        return win32gui.GetForegroundWindow() == self.window_handle

    def _ensure_foreground(self):
        if not self.window_handle:
            return
        if self._is_foreground():
            return
        try:
            win32gui.ShowWindow(self.window_handle, 5)
            win32gui.SetForegroundWindow(self.window_handle)
            time.sleep(0.02)
        except Exception:
            pass

    def _get_window_rect(self):
        if self.window_handle:
            try:
                return win32gui.GetWindowRect(self.window_handle)
            except Exception:
                return None
        return None

    def _capture_raw(self):
        if self.window_handle:
            rect = self._get_window_rect()
            if rect:
                left, top, right, bottom = rect
                monitor = {
                    "left": left + self.capture_region[0],
                    "top": top + self.capture_region[1],
                    "width": self.capture_region[2],
                    "height": self.capture_region[3],
                }
                img = self.sct.grab(monitor)
                img = np.array(img)[:, :, :3]
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                if self.crop_to_gameplay:
                    cx, cy, cw, ch = self.gameplay_crop
                    hh, ww = img.shape[:2]
                    cy2 = min(cy, hh - 1)
                    cx2 = min(cx, ww - 1)
                    ch2 = min(ch, hh - cy2)
                    cw2 = min(cw, ww - cx2)
                    if ch2 > 0 and cw2 > 0:
                        img = img[cy2 : cy2 + ch2, cx2 : cx2 + cw2]
                return img
        sct_area = self.sct.monitors[1]
        img = self.sct.grab(sct_area)
        img = np.array(img)[:, :, :3]
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        return img

    def _capture_screen(self):
        raw = self._capture_raw()
        gray = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY)
        gray = cv2.resize(gray, self.resize, interpolation=cv2.INTER_AREA)
        return gray, cv2.resize(raw, self.resize, interpolation=cv2.INTER_AREA)

    def _preprocess(self, frame):
        return frame.astype(np.float32) / 255.0

    def _is_in_game(self, gray_frame):
        if gray_frame is None:
            return self.in_game
        h, w = gray_frame.shape[:2]
        bottom_strip = gray_frame[int(h * 0.85) : h, :]
        bottom_mean = bottom_strip.mean()
        contrast = gray_frame.std()
        if bottom_mean > 60 and contrast > 30:
            return True
        return False

    def _get_progress(self, frame):
        method = self.config["progress_detection"]["method"]
        if method == "pixel":
            return self._get_progress_pixel(frame)
        return self.last_progress

    def _get_progress_pixel(self, frame):
        h, w = frame.shape[:2]
        bar_reg = self.config["progress_detection"]["bar_region"]
        bar_h = min(bar_reg[3], h)
        bar_w = min(bar_reg[2], w)
        bar_y = min(bar_reg[1], h - 1)
        bar_x = min(bar_reg[0], w - 1)
        if bar_h <= 0 or bar_w <= 0:
            return self.last_progress
        bar = frame[bar_y : bar_y + bar_h, bar_x : bar_x + bar_w]
        if bar.size == 0:
            return self.last_progress
        bright = bar > 100
        return float(bright.mean())

    def _check_death(self, rgb_frame, gray_frame):
        method = self.config["death_detection"]["method"]
        if method == "combo":
            return self._check_death_combo(rgb_frame, gray_frame)
        elif method == "dark":
            return self._check_death_dark(gray_frame)
        return False

    def _check_death_dark(self, gray_frame):
        return gray_frame.mean() < self.config["death_detection"]["dark_threshold"]

    def _check_death_combo(self, rgb_frame, gray_frame):
        mean_brightness = gray_frame.mean()
        if mean_brightness < 30:
            return True
        h, w = gray_frame.shape[:2]
        cx, cy = w // 2, h // 2
        center = gray_frame[cy - 5 : cy + 5, cx - 5 : cx + 5]
        if center.size > 0 and center.mean() > 220:
            return True
        if rgb_frame is not None:
            red = rgb_frame[:, :, 0].astype(float)
            ratio = red / (rgb_frame[:, :, 2].astype(float) + 1)
            red_flash = (ratio > 2.5).sum()
            if red_flash > (w * h * 0.3):
                return True
        return False

    def reset(self):
        self.frames.clear()
        self.raw_frames.clear()
        self.last_progress = 0.0
        self.step_count = 0
        self.done = False
        self.death_cooldown = 0
        self.in_game = False

        self._ensure_foreground()
        pydirectinput.keyUp("space")
        time.sleep(0.05)
        self._ensure_foreground()
        pydirectinput.press("esc")
        time.sleep(0.15)
        self._ensure_foreground()
        pydirectinput.press("enter")
        time.sleep(0.5)
        self._ensure_foreground()
        pydirectinput.press("enter")
        time.sleep(0.5)

        for _ in range(self.stack_size):
            gray, raw = self._capture_screen()
            proc = self._preprocess(gray)
            self.frames.append(proc)
            self.raw_frames.append(raw)
            time.sleep(self.dt)

        self.in_game = True
        return np.array(self.frames)

    def step(self, action):
        if self.done:
            return np.array(self.frames), 0.0, True, {}

        self.step_count += 1
        if self.death_cooldown > 0:
            self.death_cooldown -= 1

        self._ensure_foreground()
        if self.in_game and action == 1:
            pydirectinput.keyDown("space")
        else:
            pydirectinput.keyUp("space")

        time.sleep(self.dt)

        gray, raw = self._capture_screen()
        gray_proc = self._preprocess(gray)
        self.frames.append(gray_proc)
        self.raw_frames.append(raw)

        reward = 0.0
        if self._is_in_game(gray):
            progress = self._get_progress(raw)
            progress_delta = progress - self.last_progress
            if progress_delta > 0:
                reward += progress_delta * self.config["reward"]["progress_scale"]
            self.last_progress = max(self.last_progress, progress)

        if action == 1:
            reward += self.config["reward"]["jump_penalty"]

        if self.step_count >= self.max_steps:
            self.done = True

        if self.death_cooldown == 0 and self._check_death(raw, gray):
            reward += self.config["reward"]["death_penalty"]
            self.done = True
            pydirectinput.keyUp("space")

        return np.array(self.frames), reward, self.done, {}

    def get_last_raw_frame(self):
        if self.raw_frames:
            return self.raw_frames[-1]
        return None

    def get_last_proc_frame(self):
        if self.frames:
            return self.frames[-1]
        return None

    def close(self):
        pydirectinput.keyUp("space")
        self.sct.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
