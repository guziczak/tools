#!/usr/bin/env python3
import subprocess
import os
import sys

def main():
    # Szybkie sprawdzenie kontenera (bez formatowania)
    result = subprocess.run(
        ["docker", "ps", "-q", "-f", "name=claude-code-container"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )

    if not result.stdout.strip():
        print("❌ Kontener nie działa! Uruchom: python setup.py")
        sys.exit(1)

    # Szybka konwersja ścieżki dla Windows
    cwd = os.getcwd()
    if sys.platform == "win32" and len(cwd) > 1 and cwd[1] == ':':
        container_dir = f"/{cwd[0].lower()}{cwd[2:].replace(chr(92), '/')}"
    else:
        container_dir = cwd

    # Wykonanie claude omijając problematyczny shebang
    args = " ".join(f'"{arg}"' for arg in sys.argv[1:]) if sys.argv[1:] else ""
    subprocess.run([
        "docker", "exec", "-it",
        "-w", container_dir,
        "claude-code-container",
        "sh", "-c", f"node $(which claude) {args}"
    ])

if __name__ == "__main__":
    main()