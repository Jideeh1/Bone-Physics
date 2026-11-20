"""Build the installable Blender extension zip.

    python scripts/build_extension.py            # -> dist/bone_physics-<version>.zip

The manifest sits at the zip root, as Blender's Install from Disk expects.
"""

import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "bone_physics"
DIST = ROOT / "dist"


def version():
    text = (SRC / "blender_manifest.toml").read_text()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        sys.exit("no version in blender_manifest.toml")
    return m.group(1)


def main():
    DIST.mkdir(exist_ok=True)
    out = DIST / f"bone_physics-{version()}.zip"
    files = sorted(p for p in SRC.rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(SRC).as_posix())
    print(out)


if __name__ == "__main__":
    main()
