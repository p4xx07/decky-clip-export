"""Build the Decky installation ZIP from compiled files."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "ClipExport-0.1.1.zip"
KIT = ROOT / "ClipExportKit-0.1.1.zip"
FILES = ["plugin.json", "package.json", "main.py", "py_modules/clip_export.py", "LICENSE", "README.md", "dist/index.js"]
KIT_FILES = ["README.md", "receiver/receiver.py", "receiver/Start Clip Receiver.command",
             "receiver/install_autostart_macos.py", OUTPUT.name]

if __name__ == "__main__":
    for name in FILES:
        if not (ROOT / name).is_file():
            raise SystemExit(f"Missing {name}; run npm run build first")
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, f"Clip Export/{name}")
    print(OUTPUT)
    with ZipFile(KIT, "w", ZIP_DEFLATED) as archive:
        for name in KIT_FILES:
            archive.write(ROOT / name, f"ClipExportKit/{name}")
    print(KIT)
