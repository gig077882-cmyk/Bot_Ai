import ctypes
import ctypes.wintypes
import struct


PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400


class GDMemoryReader:
    def __init__(self, config=None):
        self.handle = None
        self.pid = None
        self.module_base = None
        self.attempts_addr = None
        self.progress_addr = None
        self.config = config or {}

    def _find_process(self):
        target = self.config.get("process_name", "GeometryDash.exe")
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
        if snapshot == -1:
            return False
        pe = ctypes.wintypes.DWORD * 4
        entry = ctypes.c_byte * 304
        entry_ptr = entry()
        ctypes.memmove(entry_ptr, pe(304, 0), 304)
        ctypes.windll.kernel32.Process32FirstW(snapshot, ctypes.byref(entry_ptr))
        found = False
        while True:
            exe_file = ctypes.create_unicode_buffer(260)
            ctypes.memmove(
                exe_file,
                ctypes.addressof(entry_ptr) + 36,
                520,
            )
            if exe_file.value and target.lower() in exe_file.value.lower():
                self.pid = struct.unpack_from("I", entry_ptr, 8)[0]
                found = True
                break
            if not ctypes.windll.kernel32.Process32NextW(
                snapshot, ctypes.byref(entry_ptr)
            ):
                break
        ctypes.windll.kernel32.CloseHandle(snapshot)
        return found

    def _open_process(self):
        self.handle = ctypes.windll.kernel32.OpenProcess(
            PROCESS_VM_READ | PROCESS_QUERY_INFORMATION,
            False,
            self.pid,
        )
        return bool(self.handle)

    def _get_module_base(self):
        snapshot = ctypes.windll.kernel32.CreateToolhelp32Snapshot(0x00000008, self.pid)
        if snapshot == -1:
            return 0
        me32 = ctypes.c_byte * 548
        entry = me32()
        ctypes.memmove(entry, ctypes.c_byte(548), 548)
        struct.pack_into("I", entry, 0, 548)
        ctypes.windll.kernel32.Module32FirstW(snapshot, ctypes.byref(entry))
        while True:
            module_name = ctypes.create_unicode_buffer(256)
            ctypes.memmove(module_name, ctypes.addressof(entry) + 12, 512)
            if module_name.value and "GeometryDash" in module_name.value:
                self.module_base = struct.unpack_from("P", entry, 32)[0]
                ctypes.windll.kernel32.CloseHandle(snapshot)
                return self.module_base
            if not ctypes.windll.kernel32.Module32NextW(
                snapshot, ctypes.byref(entry)
            ):
                break
        ctypes.windll.kernel32.CloseHandle(snapshot)
        return 0

    def _read_int(self, address):
        if not self.handle:
            return 0
        buf = ctypes.c_uint32(0)
        bytes_read = ctypes.c_size_t(0)
        ctypes.windll.kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            ctypes.byref(buf),
            ctypes.sizeof(buf),
            ctypes.byref(bytes_read),
        )
        return buf.value

    def _read_float(self, address):
        if not self.handle:
            return 0.0
        buf = ctypes.c_float(0.0)
        bytes_read = ctypes.c_size_t(0)
        ctypes.windll.kernel32.ReadProcessMemory(
            self.handle,
            ctypes.c_void_p(address),
            ctypes.byref(buf),
            ctypes.sizeof(buf),
            ctypes.byref(bytes_read),
        )
        return buf.value

    def _scan_pattern(self, pattern, mask, start=0, size=0x7FFFFFFF):
        if not self.handle:
            return 0
        addr = (self.module_base or 0) + start
        chunk = ctypes.c_byte * 4096
        bytes_read = ctypes.c_size_t(0)
        for offset in range(0, size, 4096):
            buf = chunk()
            ctypes.windll.kernel32.ReadProcessMemory(
                self.handle,
                ctypes.c_void_p(addr + offset),
                ctypes.byref(buf),
                ctypes.sizeof(buf),
                ctypes.byref(bytes_read),
            )
            for i in range(bytes_read.value - len(pattern)):
                match = True
                for j in range(len(pattern)):
                    if mask[j] == "x" and buf[i + j] != pattern[j]:
                        match = False
                        break
                if match:
                    return addr + offset + i
        return 0

    def connect(self):
        if not self._find_process():
            raise RuntimeError("GeometryDash.exe process not found")
        if not self._open_process():
            raise RuntimeError("Failed to open process")
        self._get_module_base()
        return True

    def find_attempts_address(self):
        if not self.module_base:
            return False
        offsets = self.config.get("attempts_offsets", [])
        if offsets:
            base_addr = self.module_base + offsets[0]
            addr = base_addr
            for off in offsets[1:]:
                ptr = self._read_int(addr)
                if not ptr:
                    return False
                addr = ptr + off
            self.attempts_addr = addr
            return bool(addr)
        return False

    def read_attempts(self):
        if not self.attempts_addr:
            return 0
        return self._read_int(self.attempts_addr)

    def find_progress_address(self, offsets=None):
        if not self.module_base:
            return False
        if not offsets:
            offsets = self.config.get("progress_offsets", [])
        if not offsets:
            return False
        base_addr = self.module_base + offsets[0]
        addr = base_addr
        for off in offsets[1:]:
            ptr = self._read_int(addr)
            if not ptr:
                return False
            addr = ptr + off
        self.progress_addr = addr
        return bool(addr)

    def read_progress(self):
        if not self.progress_addr:
            return 0.0
        return self._read_float(self.progress_addr)

    def find_value_address(self, value, value_type="int"):
        if not self.handle or not self.module_base:
            return 0
        size = 0x1000000
        chunk_size = 4096
        chunk = ctypes.c_byte * chunk_size
        bytes_read = ctypes.c_size_t(0)
        for offset in range(0, size, chunk_size):
            buf = chunk()
            ctypes.windll.kernel32.ReadProcessMemory(
                self.handle,
                ctypes.c_void_p(self.module_base + offset),
                ctypes.byref(buf),
                ctypes.sizeof(buf),
                ctypes.byref(bytes_read),
            )
            if value_type == "int":
                fmt, sz = "I", 4
            elif value_type == "float":
                fmt, sz = "f", 4
            elif value_type == "short":
                fmt, sz = "H", 2
            else:
                fmt, sz = "I", 4
            for i in range(0, bytes_read.value - sz, sz):
                data = bytes(buf[i : i + sz])
                if value_type == "int":
                    val = struct.unpack_from("I", data)[0]
                elif value_type == "float":
                    val = struct.unpack_from("f", data)[0]
                else:
                    val = struct.unpack_from("I", data)[0]
                if val == value:
                    addr = self.module_base + offset + i
                    if self._is_stable_address(addr, value, value_type):
                        return addr
        return 0

    def _is_stable_address(self, addr, value, value_type="int"):
        for _ in range(3):
            import time
            time.sleep(0.1)
            if value_type == "int":
                v = self._read_int(addr)
            elif value_type == "float":
                v = self._read_float(addr)
            else:
                v = self._read_int(addr)
            if v != value:
                return False
        return True

    def set_address(self, addr_type, address):
        if addr_type == "attempts":
            self.attempts_addr = address
        elif addr_type == "progress":
            self.progress_addr = address

    def close(self):
        if self.handle:
            ctypes.windll.kernel32.CloseHandle(self.handle)
            self.handle = None
