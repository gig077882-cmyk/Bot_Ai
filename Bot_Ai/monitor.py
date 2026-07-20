import tkinter as tk
from tkinter import ttk
import threading
import time
from memory_reader import GDMemoryReader


class GDMonitor:
    def __init__(self, config):
        self.config = config
        self.reader = GDMemoryReader(config.get("memory", {}))
        self.connected = False
        self.attempts = 0
        self.progress = 0.0
        self.prev_attempts = 0
        self.deaths_since_check = 0
        self.running = True

        self.root = tk.Tk()
        self.root.title("GD AI Monitor")
        self.root.geometry("350x250")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        style = ttk.Style()
        style.theme_use("clam")

        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="GEOMETRY DASH AI", font=("Arial", 14, "bold")).pack(
            pady=(0, 10)
        )

        sep = ttk.Separator(frame, orient="horizontal")
        sep.pack(fill=tk.X, pady=5)

        info_frame = ttk.Frame(frame)
        info_frame.pack(fill=tk.BOTH, expand=True)

        self.connect_label = ttk.Label(
            info_frame, text="Status: Connecting...", font=("Arial", 10)
        )
        self.connect_label.pack(anchor=tk.W, pady=2)

        self.attempts_label = ttk.Label(
            info_frame, text="Attempts: --", font=("Arial", 11, "bold")
        )
        self.attempts_label.pack(anchor=tk.W, pady=2)

        self.progress_label = ttk.Label(
            info_frame, text="Progress: --%", font=("Arial", 11, "bold")
        )
        self.progress_label.pack(anchor=tk.W, pady=2)

        self.deaths_label = ttk.Label(
            info_frame, text="Deaths (session): --", font=("Arial", 10)
        )
        self.deaths_label.pack(anchor=tk.W, pady=2)

        self.attempts_per_min_label = ttk.Label(
            info_frame, text="Attempts/min: --", font=("Arial", 10)
        )
        self.attempts_per_min_label.pack(anchor=tk.W, pady=2)

        sep2 = ttk.Separator(frame, orient="horizontal")
        sep2.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        self.find_btn = ttk.Button(
            btn_frame, text="Find Addresses", command=self._find_addresses
        )
        self.find_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.scan_btn = ttk.Button(
            btn_frame, text="Scan Attempts Value", command=self._scan_attempts
        )
        self.scan_btn.pack(side=tk.LEFT, padx=5)

        self.quit_btn = ttk.Button(
            btn_frame, text="Quit", command=self._on_close
        )
        self.quit_btn.pack(side=tk.RIGHT)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _find_addresses(self):
        threading.Thread(target=self._find_addresses_worker, daemon=True).start()

    def _find_addresses_worker(self):
        self.find_btn.config(state=tk.DISABLED)
        try:
            self.reader.connect()
            c = self.reader.find_attempts_address()
            p = self.reader.find_progress_address()
            if c:
                self._update_status(f"Attempts addr found: 0x{self.reader.attempts_addr:X}")
            if p:
                self._update_status(f"Progress addr found: 0x{self.reader.progress_addr:X}")
            if not c and not p:
                self._update_status("No addresses found. Use scan or set offsets in config.")
        except Exception as e:
            self._update_status(f"Error: {e}")
        finally:
            self.find_btn.config(state=tk.NORMAL)

    def _scan_attempts(self):
        threading.Thread(target=self._scan_attempts_worker, daemon=True).start()

    def _scan_attempts_worker(self):
        self.scan_btn.config(state=tk.DISABLED)
        try:
            self._update_status("Enter your current attempt count in GD...")
            time.sleep(3)
            if not self.reader.handle:
                self.reader.connect()
            current = self.reader.attempts
            addr = self.reader.find_value_address(current, "int")
            if addr:
                self.reader.set_address("attempts", addr)
                self._update_status(f"Found at 0x{addr:X}. Add this to config attempts_offsets.")
            else:
                self._update_status("Address not found. Make sure GD is on a level screen.")
        except Exception as e:
            self._update_status(f"Error: {e}")
        finally:
            self.scan_btn.config(state=tk.NORMAL)

    def _update_status(self, msg):
        self.root.after(0, lambda: self.connect_label.config(text=f"Status: {msg}"))

    def _update_ui(self):
        if self.connected:
            self.attempts_label.config(text=f"Attempts: {self.attempts}")
            self.progress_label.config(text=f"Progress: {self.progress:.1f}%")
            self.deaths_label.config(text=f"Deaths (session): {self.deaths_since_check}")
        self.root.after(1000, self._update_ui)

    def _read_loop(self):
        while self.running:
            try:
                if not self.connected:
                    try:
                        self.reader.connect()
                        self.connected = True
                        self.prev_attempts = self.reader.read_attempts()
                        self.root.after(
                            0,
                            lambda: self.connect_label.config(text="Status: Connected"),
                        )
                    except RuntimeError as e:
                        self.root.after(
                            0,
                            lambda: self.connect_label.config(
                                text=f"Status: Waiting for GD ({e})"
                            ),
                        )
                        time.sleep(2)
                        continue

                self.attempts = self.reader.read_attempts()
                if self.attempts > self.prev_attempts:
                    self.deaths_since_check += self.attempts - self.prev_attempts
                self.prev_attempts = self.attempts

                self.progress = self.reader.read_progress()

            except Exception:
                self.connected = False
                self.root.after(
                    0,
                    lambda: self.connect_label.config(text="Status: Disconnected"),
                )

            time.sleep(0.5)

    def run(self):
        t = threading.Thread(target=self._read_loop, daemon=True)
        t.start()
        self.root.after(1000, self._update_ui)
        self.root.mainloop()

    def _on_close(self):
        self.running = False
        self.reader.close()
        self.root.destroy()


if __name__ == "__main__":
    import yaml
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)
    app = GDMonitor(cfg)
    app.run()
