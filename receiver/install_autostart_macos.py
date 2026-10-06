"""Install the receiver as a per-user macOS LaunchAgent after pairing."""

import os
import plistlib
import subprocess
import sys
from pathlib import Path


def main():
    if sys.platform != "darwin":
        raise SystemExit("This installer is for macOS")
    script = Path(__file__).resolve().parent / "receiver.py"
    label = "local.decky-clip-export.receiver"
    plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    log = Path.home() / "Library" / "Logs" / "ClipExport-receiver.log"
    plist.parent.mkdir(parents=True, exist_ok=True)
    log.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "Label": label,
        "ProgramArguments": [sys.executable, str(script)],
        "WorkingDirectory": str(script.parent),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
    }
    plist.write_bytes(plistlib.dumps(payload))
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(plist)], capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist)], check=True)
    print(f"Receiver starts at login. Log and pairing code: {log}")
    print(f"To remove it: launchctl bootout {domain} {plist}")


if __name__ == "__main__":
    main()
