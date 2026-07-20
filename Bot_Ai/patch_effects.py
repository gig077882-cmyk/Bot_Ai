import os
import shutil


BACKUP_SUFFIX = ".backup"


def patch_plist(filepath, dry_run=False):
    with open(filepath, "rb") as f:
        data = f.read()

    original = data
    modified = False

    patches = [
        (b"<key>maxParticles</key>\n\t<integer>\\d+</integer>",
         b"<key>maxParticles</key>\n\t<integer>0</integer>"),
        (b"<key>emissionRate</key>\n\t<real>[^<]+</real>",
         b"<key>emissionRate</key>\n\t<real>0</real>"),
        (b"<key>speed</key>\n\t<real>[^<]+</real>",
         b"<key>speed</key>\n\t<real>0</real>"),
        (b"<key>speedVariance</key>\n\t<real>[^<]+</real>",
         b"<key>speedVariance</key>\n\t<real>0</real>"),
        (b"<key>duration</key>\n\t<real>[^<]+</real>",
         b"<key>duration</key>\n\t<real>0</real>"),
        (b"<key>sourcePositionVariancex</key>",
         b"<key>sourcePositionVariancex</key>"),
        (b"<key>angleVariance</key>\n\t<real>[^<]+</real>",
         b"<key>angleVariance</key>\n\t<real>0</real>"),
        (b"<key>radialAccelVariance</key>\n\t<real>[^<]+</real>",
         b"<key>radialAccelVariance</key>\n\t<real>0</real>"),
        (b"<key>tangentialAccelVariance</key>\n\t<real>[^<]+</real>",
         b"<key>tangentialAccelVariance</key>\n\t<real>0</real>"),
        (b"<key>rotatePerSecondVariance</key>\n\t<real>[^<]+</real>",
         b"<key>rotatePerSecondVariance</key>\n\t<real>0</real>"),
    ]

    import re
    for pattern, replacement in patches:
        new_data = re.sub(pattern, replacement, data)
        if new_data != data:
            modified = True
            data = new_data

    if modified and not dry_run:
        backup_path = filepath + BACKUP_SUFFIX
        if not os.path.exists(backup_path):
            shutil.copy2(filepath, backup_path)
            print(f"  Backup: {backup_path}")
        with open(filepath, "wb") as f:
            f.write(data)
        return True

    return modified


def patch_directory(resources_dir, dry_run=False):
    if not os.path.isdir(resources_dir):
        print(f"Error: {resources_dir} not found")
        return

    plist_files = []
    for root, dirs, files in os.walk(resources_dir):
        for f in files:
            if f.endswith(".plist"):
                plist_files.append(os.path.join(root, f))

    patched_count = 0
    skip_count = 0

    print(f"Found {len(plist_files)} .plist files")
    if dry_run:
        print("DRY RUN - no files will be modified\n")

    for path in plist_files:
        try:
            patched = patch_plist(path, dry_run)
            if patched:
                rel = os.path.relpath(path, resources_dir)
                print(f"  Patched: {rel}")
                patched_count += 1
            else:
                skip_count += 1
        except Exception as e:
            print(f"  Error: {path} - {e}")

    print(f"\nDone: {patched_count} patched, {skip_count} skipped")
    if not dry_run:
        print("Backups saved with .backup extension")
    print("\nRestore backups with:")
    print(f'  python -c "import os, glob; [os.rename(f, f[:-7]) for f in glob.glob(r\'{resources_dir}\\\\**\\\\*.backup\', recursive=True)]"')


def restore_backups(resources_dir):
    if not os.path.isdir(resources_dir):
        print(f"Error: {resources_dir} not found")
        return
    restored = 0
    for root, dirs, files in os.walk(resources_dir):
        for f in files:
            if f.endswith(BACKUP_SUFFIX):
                src = os.path.join(root, f)
                dst = src[: -len(BACKUP_SUFFIX)]
                os.replace(src, dst)
                print(f"  Restored: {os.path.relpath(dst, resources_dir)}")
                restored += 1
    print(f"\nRestored {restored} files")


if __name__ == "__main__":
    import sys

    gd_dir = getattr(sys, "_MEIPASS", None) or os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
    resources_dir = os.path.join(gd_dir, "Resources")

    if not os.path.isdir(resources_dir):
        resources_dir = input("GD Resources path: ").strip()

    print("GEOMETRY DASH - Effect Patcher")
    print("1. Disable effects (particles)")
    print("2. Restore from backup")
    print("3. Dry run (see what would be changed)")
    choice = input("Choice (1/2/3): ").strip()

    if choice == "2":
        restore_backups(resources_dir)
    elif choice == "3":
        patch_directory(resources_dir, dry_run=True)
    else:
        patch_directory(resources_dir)
