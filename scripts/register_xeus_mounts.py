"""Record xeus mount tarballs in the kernel's empack_env_meta.json.

jupyterlite-xeus packs each --XeusAddon.mounts entry as kernel_packages/mount_N.tar.gz,
but the built metadata can omit them. The kernel only extracts entries listed under
"mounts", so without this step the rpds package and a2ui_preload.pth never reach
the kernel filesystem.
"""

import json
import re
import sys
from pathlib import Path

MOUNT_RE = re.compile(r"^mount_(\d+)\.tar\.gz$")
META_NAME = "empack_env_meta.json"
PACKAGES_DIR = "kernel_packages"


def register_mounts(env_dir):
    env_dir = Path(env_dir)
    meta_path = env_dir / META_NAME
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    mounts = meta.get("mounts", [])
    listed = {item["filename"] for item in mounts}
    tarballs = sorted(
        (p.name for p in (env_dir / PACKAGES_DIR).iterdir() if MOUNT_RE.match(p.name)),
        key=lambda name: int(MOUNT_RE.match(name).group(1)),
    )
    for name in tarballs:
        if name not in listed:
            mounts.append({"name": name, "filename": name})
    meta["mounts"] = mounts

    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return [item["filename"] for item in mounts]


def main(argv):
    env_dir = argv[1] if len(argv) > 1 else "dist/xeus/xeus-kernel"
    for name in register_mounts(env_dir):
        print(f"mount: {name}")


if __name__ == "__main__":
    main(sys.argv)
