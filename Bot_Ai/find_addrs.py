import time
import yaml
from memory_reader import GDMemoryReader


def update_config(attempts_addr=None, progress_addr=None):
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    changed = False
    if attempts_addr is not None:
        config["memory"]["attempts_offsets"] = [attempts_addr]
        changed = True
    if progress_addr is not None:
        config["memory"]["progress_offsets"] = [progress_addr]
        changed = True

    if changed:
        with open("config.yaml", "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        print("Saved to config.yaml")


def scan_attempts():
    print("=== Attempt Count Scanner ===")
    print("1. Open GD and go to a level")
    print("2. Note your current attempt count")
    print()

    reader = GDMemoryReader()
    try:
        reader.connect()
        print(f"Connected! Module base: 0x{reader.module_base:X}")
    except RuntimeError as e:
        print(f"Error: {e}")
        return

    try:
        val = int(input("Enter current attempt count: "))
    except ValueError:
        print("Invalid number")
        reader.close()
        return

    print("Scanning memory... (this may take a moment)")

    addrs_before = reader.find_value_address(val, "int")
    if not addrs_before:
        print("Address not found on first scan.")
        print("Try making an attempt in GD and scanning again.")
        reader.close()
        return

    print(f"Press ENTER after making 1 more attempt...")
    input()

    val2 = int(input(f"Enter new attempt count (should be > {val}): "))

    addrs_after = reader.find_value_address(val2, "int")
    if not addrs_after:
        print("Could not find new value. Try again.")
        reader.close()
        return

    if addrs_before == addrs_after:
        offset = addrs_before - reader.module_base
        print(f"\nStable address found!")
        print(f"  Absolute: 0x{addrs_before:X}")
        print(f"  Offset from base: 0x{offset:X}")
        print(f"  Offset (decimal): {offset}")
        reader.set_address("attempts", addrs_before)
        print(f"  Verified: attempts = {reader.read_attempts()}")
        return addrs_before
    else:
        print("Address changed between scans. Repeat the process.")
        reader.close()
        return None


def find_any_address():
    print("=== Manual Address Finder ===")
    print("Use Cheat Engine to find the static address.")
    print()
    try:
        offset = int(input("Enter offset from module base (hex or decimal): "), 0)
    except ValueError:
        print("Invalid number")
        return

    reader = GDMemoryReader()
    try:
        reader.connect()
        addr = reader.module_base + offset
        reader.set_address("attempts", addr)
        print(f"Address: 0x{addr:X}")
        print(f"Read value: {reader.read_attempts()}")
        return addr
    except RuntimeError as e:
        print(f"Error: {e}")
        return None
    finally:
        reader.close()


def main():
    print("GEOMETRY DASH - Memory Address Finder")
    print("=" * 40)
    print()
    print("1. Auto-scan for attempt count")
    print("2. Enter manual offset (from Cheat Engine)")
    print("3. Just connect and show base address")
    choice = input("Select (1/2/3): ").strip()

    if choice == "1":
        addr = scan_attempts()
        if addr:
            save = input("Save to config.yaml? (y/n): ").strip().lower()
            if save == "y":
                update_config(attempts_addr=addr)
    elif choice == "2":
        addr = find_any_address()
        if addr:
            save = input("Save to config.yaml? (y/n): ").strip().lower()
            if save == "y":
                update_config(attempts_addr=addr)
    elif choice == "3":
        reader = GDMemoryReader()
        try:
            reader.connect()
            print(f"Process ID: {reader.pid}")
            print(f"Module Base: 0x{reader.module_base:X}")
        except RuntimeError as e:
            print(f"Error: {e}")
        finally:
            reader.close()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
